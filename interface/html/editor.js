const byId = (id) => document.getElementById(id);

let api = null;
let currentState = null;
let plotCurves = [];

function setMessage(id, message, type = "") {
    const element = byId(id);
    element.textContent = message || "";
    element.className = `message ${type}`;
}

function setConnection(ready, message) {
    byId("connection-status").textContent = message;
    byId("connection-dot").classList.toggle("ready", ready);
}

function addOption(select, value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
}

function renderVariables(variables) {
    const container = byId("variables-list");
    container.replaceChildren();

    if (!variables.length) {
        container.textContent = "Переменных пока нет";
        container.className = "data-list empty";
        return;
    }

    container.className = "data-list";

    for (const variable of variables) {
        const item = document.createElement("div");
        item.className = "data-item";

        const name = document.createElement("span");
        name.textContent = variable.name;

        const value = document.createElement("span");
        value.textContent = variable.value;

        item.append(name, value);
        container.appendChild(item);
    }
}

function renderFunctions(functions) {
    const container = byId("functions-list");
    container.replaceChildren();

    if (!functions.length) {
        container.textContent = "Функций пока нет";
        container.className = "tag-list empty";
        return;
    }

    container.className = "tag-list";

    for (const name of functions) {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = name;
        container.appendChild(tag);
    }
}

function updatePlotColumns() {
    const datasetSelect = byId("plot-dataset");
    const xSelect = byId("plot-x");
    const ySelect = byId("plot-y");

    const dataset = currentState?.datasets.find(
        item => item.name === datasetSelect.value
    );

    xSelect.replaceChildren();
    ySelect.replaceChildren();

    if (!dataset || dataset.numeric_columns.length < 1) {
        addOption(xSelect, "", "Нет числовых столбцов");
        addOption(ySelect, "", "Нет числовых столбцов");
        xSelect.disabled = true;
        ySelect.disabled = true;
        byId("add-plot-curve").disabled = true;
        return;
    }

    for (const column of dataset.numeric_columns) {
        addOption(xSelect, column, column);
        addOption(ySelect, column, column);
    }

    if (dataset.numeric_columns.length > 1) {
        ySelect.selectedIndex = 1;
    }

    xSelect.disabled = false;
    ySelect.disabled = false;
    byId("add-plot-curve").disabled = false;
}

function renderCurveList() {
    const container = byId("plot-curves-list");
    container.replaceChildren();

    if (!plotCurves.length) {
        container.textContent = "Кривые не добавлены";
        container.className = "curve-list empty";
        byId("render-plot").disabled = true;
        return;
    }

    container.className = "curve-list";

    plotCurves.forEach((curve, index) => {
        const item = document.createElement("div");
        item.className = "curve-item";

        const label = document.createElement("span");
        label.textContent =
            `${curve.label} · ${curve.dataset_name} (${curve.x_column}, ${curve.y_column})`;

        const remove = document.createElement("button");
        remove.className = "dataset-remove";
        remove.textContent = "×";
        remove.title = "Удалить кривую";
        remove.addEventListener("click", () => {
            plotCurves.splice(index, 1);
            renderCurveList();
        });

        item.append(label, remove);
        container.appendChild(item);
    });

    byId("render-plot").disabled = false;
}

function addPlotCurve() {
    const datasetName = byId("plot-dataset").value;
    const xColumn = byId("plot-x").value;
    const yColumn = byId("plot-y").value;

    if (!datasetName || !xColumn || !yColumn) {
        setMessage("plot-message", "Выберите набор данных и столбцы X/Y", "error");
        return;
    }

    const label = byId("plot-curve-label").value.trim()
        || `${datasetName}: ${yColumn}`;

    plotCurves.push({
        dataset_name: datasetName,
        x_column: xColumn,
        y_column: yColumn,
        label,
    });

    byId("plot-curve-label").value = "";
    renderCurveList();
    setMessage("plot-message", `Добавлена кривая: ${label}`, "success");
}

function updateProcessingControls() {
    const datasetSelect = byId("process-dataset");
    const columnSelect = byId("process-column");
    const xSelect = byId("process-x-column");
    const dataset = currentState?.datasets.find(item => item.name === datasetSelect.value);
    columnSelect.replaceChildren();
    xSelect.replaceChildren();
    addOption(xSelect, "", "Индекс строк");
    if (!dataset) {
        addOption(columnSelect, "", "Нет данных");
        columnSelect.disabled = true;
        xSelect.disabled = true;
        byId("run-processing").disabled = true;
        return;
    }
    for (const column of dataset.numeric_columns) {
        addOption(columnSelect, column, column);
        addOption(xSelect, column, column);
    }
    // Prefer the first numeric column as X (usually time) and the second as Y.
    if (dataset.numeric_columns.length > 1) {
        columnSelect.selectedIndex = 1;
        xSelect.selectedIndex = 1;
    } else if (dataset.numeric_columns.length === 1) {
        xSelect.selectedIndex = 0; // use row index when no separate X column exists
    }
    columnSelect.disabled = dataset.numeric_columns.length === 0;
    xSelect.disabled = dataset.numeric_columns.length === 0;
    byId("run-processing").disabled = false;
}
function updateProcessingOperation() {
    const operation = byId("process-operation").value;
    byId("process-window-label").hidden = operation !== "smooth";
    byId("process-column").disabled = operation === "statistics" || !currentState?.datasets.length;
    byId("process-x-column").disabled = !["derivative", "integrate"].includes(operation);
}
async function runProcessing() {
    const operation = byId("process-operation").value;
    const name = byId("process-dataset").value;
    const column = byId("process-column").value;
    const xColumn = byId("process-x-column").value || null;
    const window = Number(byId("process-window").value);
    try {
        const response = await api.process_dataset(name, operation, column, {
            x_column: xColumn,
            window,
        });
        if (!response.ok) {
            setMessage("processing-message", response.error, "error");
            return;
        }
        const descriptions = {
            smooth: "Скользящее среднее: каждое значение заменяется средним в окне указанного размера.",
            derivative: "Конечная разность: (Y следующей строки − Y текущей строки) / (X следующей строки − X текущей строки). Для последней строки используется предыдущий интервал.",
            integrate: "Численное интегрирование методом трапеций: ∫Y dX.",
            statistics: "Описательная статистика для всех числовых столбцов: count — число значений; mean — среднее; std — стандартное отклонение; min/max — минимум/максимум; 25%/50%/75% — квартили."
        };
        byId("processing-result").textContent =
            (descriptions[operation] || "") + "\\n\\n" +
            (operation === "integrate"
                ? `${response.message} = ${response.result}`
                : (response.result ?? response.message ?? ""));
        if (response.state) renderState(response.state);
        if (response.dataset_name) {
            byId("table-dataset").value = response.dataset_name;
            await refreshTable();
        }
        setMessage("processing-message", response.message, "success");
    } catch (error) {
        setMessage("processing-message", error.message, "error");
    }
}

function renderDatasets(datasets) {
    const container = byId("datasets-list");
    const plotSelect = byId("plot-dataset");
    const tableSelect = byId("table-dataset");
    const processSelect = byId("process-dataset");

    const previousPlot = plotSelect.value;
    const previousTable = tableSelect.value;
    const previousProcess = processSelect.value;

    container.replaceChildren();
    plotSelect.replaceChildren();
    tableSelect.replaceChildren();
    processSelect.replaceChildren();

    if (!datasets.length) {
        container.textContent = "CSV-файлы ещё не загружены";
        container.className = "dataset-list empty";
        addOption(plotSelect, "", "Нет данных");
        addOption(tableSelect, "", "Нет данных");
        addOption(processSelect, "", "Нет данных");
        processSelect.disabled = true;
        byId("run-processing").disabled = true;
        plotSelect.disabled = true;
        tableSelect.disabled = true;
        byId("refresh-table").disabled = true;
        updatePlotColumns();
        renderCurveList();
        renderTablePlaceholder("Загрузите CSV для просмотра таблицы");
        return;
    }

    container.className = "dataset-list";
    plotSelect.disabled = false;
    tableSelect.disabled = false;
    processSelect.disabled = false;
    byId("refresh-table").disabled = false;

    addOption(plotSelect, "", "Выберите набор");
    addOption(tableSelect, "", "Выберите набор");
    addOption(processSelect, "", "Выберите набор");

    for (const dataset of datasets) {
        const item = document.createElement("div");
        item.className = "dataset-item";

        const details = document.createElement("div");
        const name = document.createElement("div");
        name.textContent = dataset.name;

        const meta = document.createElement("div");
        meta.className = "dataset-meta";
        meta.textContent =
            `${dataset.rows} строк · ${dataset.columns.length} столбцов`;

        details.append(name, meta);

        const actions = document.createElement("div");
        actions.className = "dataset-actions";

        const exportButton = document.createElement("button");
        exportButton.className = "dataset-remove";
        exportButton.textContent = "Экспорт";
        exportButton.addEventListener("click", () => exportDataset(dataset.name));

        const remove = document.createElement("button");
        remove.className = "dataset-remove";
        remove.textContent = "Удалить";
        remove.addEventListener("click", () => removeDataset(dataset.name));

        actions.append(exportButton, remove);
        item.append(details, actions);
        container.appendChild(item);

        addOption(plotSelect, dataset.name, dataset.name);
        addOption(tableSelect, dataset.name, dataset.name);
        addOption(processSelect, dataset.name, dataset.name);
    }

    plotSelect.value = datasets.some(item => item.name === previousPlot)
        ? previousPlot
        : datasets[0].name;

    tableSelect.value = datasets.some(item => item.name === previousTable)
        ? previousTable
        : datasets[0].name;

    processSelect.value = datasets.some(item => item.name === previousProcess) ? previousProcess : datasets[0].name;
    updatePlotColumns();
    updateProcessingControls();
    updateProcessingOperation();
    refreshTable();
}

function renderState(state, updateEditor = false) {
    currentState = state;

    if (updateEditor) {
        byId("formula-input").value = state.lines.join("\n");
    }

    renderVariables(state.variables);
    renderFunctions(state.functions);
    renderDatasets(state.datasets);
}

async function refreshState(updateEditor = false) {
    const state = await api.get_state();
    renderState(state, updateEditor);
}

async function applyFormulas() {
    const lines = byId("formula-input").value
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean);

    try {
        const response = await api.set_lines(lines);

        if (!response.ok) {
            setMessage("formula-message", response.error, "error");
            return;
        }

        renderState(response.state);
        setMessage("formula-message", response.message, "success");
    } catch (error) {
        setMessage("formula-message", error.message, "error");
    }
}

function addFormulaLine() {
    const editor = byId("formula-input");
    const position = editor.selectionStart;
    const before = editor.value.slice(0, position);
    const after = editor.value.slice(position);
    const insertion = before && !before.endsWith("\n") ? "\n" : "";

    editor.value = before + insertion + after;
    editor.focus();
    const cursor = before.length + insertion.length;
    editor.setSelectionRange(cursor, cursor);
}

function removeFormulaLine() {
    const editor = byId("formula-input");
    const lines = editor.value.split(/\r?\n/);
    if (lines.length <= 1) {
        editor.value = "";
    } else {
        lines.pop();
        editor.value = lines.join("\n");
    }
    editor.focus();
}

async function evaluateExpression() {
    const expression = byId("expression-input").value;

    try {
        const response = await api.evaluate(expression);

        if (!response.ok) {
            byId("evaluation-result").textContent = "Ошибка вычисления";
            setMessage("evaluation-message", response.error, "error");
            return;
        }

        byId("evaluation-result").textContent = response.result;
        setMessage("evaluation-message", "Готово", "success");
    } catch (error) {
        setMessage("evaluation-message", error.message, "error");
    }
}

async function loadCsv() {
    const name = byId("dataset-name").value.trim() || null;

    try {
        const response = await api.select_csv_file(name);
        if (response.cancelled) return;

        if (!response.ok) {
            setMessage("dataset-message", response.error, "error");
            return;
        }

        byId("dataset-name").value = "";
        renderState(response.state);
        setMessage("dataset-message", response.message, "success");
    } catch (error) {
        setMessage("dataset-message", error.message, "error");
    }
}

async function exportDataset(name) {
    try {
        const response = await api.select_export_csv_file(name);
        if (response.cancelled) return;

        if (!response.ok) {
            setMessage("dataset-message", response.error, "error");
            return;
        }

        setMessage("dataset-message", response.message, "success");
    } catch (error) {
        setMessage("dataset-message", error.message, "error");
    }
}

async function removeDataset(name) {
    try {
        const response = await api.remove_dataset(name);

        if (!response.ok) {
            setMessage("dataset-message", response.error, "error");
            return;
        }

        plotCurves = plotCurves.filter(curve => curve.dataset_name !== name);
        renderCurveList();
        renderState(response.state);
        setMessage("dataset-message", `Удалено: ${name}`, "success");
    } catch (error) {
        setMessage("dataset-message", error.message, "error");
    }
}

function renderTablePlaceholder(message) {
    const container = byId("table-view");
    container.replaceChildren();

    const placeholder = document.createElement("div");
    placeholder.className = "empty";
    placeholder.textContent = message;
    container.appendChild(placeholder);
}

async function refreshTable() {
    const name = byId("table-dataset").value;
    if (!name) {
        renderTablePlaceholder("Выберите набор данных");
        byId("table-info").textContent = "";
        return;
    }

    try {
        const response = await api.preview_data(name, 100);

        if (!response.ok) {
            setMessage("table-message", response.error, "error");
            return;
        }

        const table = document.createElement("table");
        table.className = "data-table";

        const thead = document.createElement("thead");
        const header = document.createElement("tr");
        for (const column of response.columns) {
            const th = document.createElement("th");
            th.textContent = column;
            header.appendChild(th);
        }
        thead.appendChild(header);

        const tbody = document.createElement("tbody");
        for (const row of response.rows) {
            const tr = document.createElement("tr");
            for (const value of row) {
                const td = document.createElement("td");
                td.textContent = value === null ? "—" : String(value);
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }

        table.append(thead, tbody);
        byId("table-view").replaceChildren(table);

        byId("table-info").textContent =
            `Показано ${response.shown_rows} из ${response.total_rows} строк`;

        setMessage("table-message", "Таблица обновлена", "success");
    } catch (error) {
        setMessage("table-message", error.message, "error");
    }
}

async function renderPlot() {
    if (!plotCurves.length) {
        setMessage("plot-message", "Добавьте хотя бы одну кривую", "error");
        return;
    }

    const title = byId("plot-title").value.trim() || null;

    try {
        const response = await api.render_plot_curves(plotCurves, title);

        if (!response.ok) {
            setMessage("plot-message", response.error, "error");
            return;
        }

        byId("plot-image").src = response.image;
        byId("plot-image").hidden = false;
        byId("plot-placeholder").hidden = true;
        setMessage(
            "plot-message",
            `Построено кривых: ${response.curve_count}`,
            "success",
        );
    } catch (error) {
        setMessage("plot-message", error.message, "error");
    }
}

async function initialize() {
    if (api) return;
    api = window.pywebview.api;

    try {
        await refreshState(true);
        setConnection(true, "Python подключён");
    } catch (error) {
        setConnection(false, "Ошибка подключения");
        console.error(error);
    }
}

byId("apply-formulas").addEventListener("click", applyFormulas);
byId("clear-formulas").addEventListener("click", () => {
    byId("formula-input").value = "";
    applyFormulas();
});
byId("add-formula-line").addEventListener("click", addFormulaLine);
byId("remove-formula-line").addEventListener("click", removeFormulaLine);
byId("formula-input").addEventListener("keydown", event => {
    if (event.ctrlKey && event.key === "Enter") applyFormulas();
});

byId("evaluate-button").addEventListener("click", evaluateExpression);
byId("expression-input").addEventListener("keydown", event => {
    if (event.key === "Enter") evaluateExpression();
});

byId("load-csv").addEventListener("click", loadCsv);
byId("plot-dataset").addEventListener("change", updatePlotColumns);
byId("add-plot-curve").addEventListener("click", addPlotCurve);
byId("render-plot").addEventListener("click", renderPlot);
byId("table-dataset").addEventListener("change", refreshTable);
byId("process-dataset").addEventListener("change", updateProcessingControls);
byId("process-operation").addEventListener("change", updateProcessingOperation);
byId("run-processing").addEventListener("click", runProcessing);
byId("refresh-table").addEventListener("click", refreshTable);

window.addEventListener("pywebviewready", initialize);
if (window.pywebview?.api) initialize();

