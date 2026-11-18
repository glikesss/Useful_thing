const byId = (id) => document.getElementById(id);

let api = null;
let currentState = null;

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
        byId("render-plot").disabled = true;
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
    byId("render-plot").disabled = false;
}

function renderDatasets(datasets) {
    const container = byId("datasets-list");
    const datasetSelect = byId("plot-dataset");
    const selected = datasetSelect.value;

    container.replaceChildren();
    datasetSelect.replaceChildren();

    if (!datasets.length) {
        container.textContent = "CSV-файлы ещё не загружены";
        container.className = "dataset-list empty";
        addOption(datasetSelect, "", "Нет данных");
        datasetSelect.disabled = true;
        updatePlotColumns();
        return;
    }

    container.className = "dataset-list";
    datasetSelect.disabled = false;

    addOption(datasetSelect, "", "Выберите набор");

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

        const remove = document.createElement("button");
        remove.className = "dataset-remove";
        remove.textContent = "Удалить";
        remove.addEventListener("click", () => removeDataset(dataset.name));

        item.append(details, remove);
        container.appendChild(item);

        addOption(datasetSelect, dataset.name, dataset.name);
    }

    if (datasets.some(item => item.name === selected)) {
        datasetSelect.value = selected;
    } else if (datasets.length === 1) {
        datasetSelect.value = datasets[0].name;
    }

    updatePlotColumns();
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

async function removeDataset(name) {
    try {
        const response = await api.remove_dataset(name);

        if (!response.ok) {
            setMessage("dataset-message", response.error, "error");
            return;
        }

        renderState(response.state);
        setMessage("dataset-message", `Удалено: ${name}`, "success");
    } catch (error) {
        setMessage("dataset-message", error.message, "error");
    }
}

async function renderPlot() {
    const dataset = byId("plot-dataset").value;
    const x = byId("plot-x").value;
    const y = byId("plot-y").value;
    const title = byId("plot-title").value.trim() || null;

    if (!dataset || !x || !y) {
        setMessage("plot-message", "Выберите набор и оба столбца", "error");
        return;
    }

    try {
        const response = await api.render_plot(dataset, x, y, title);

        if (!response.ok) {
            setMessage("plot-message", response.error, "error");
            return;
        }

        byId("plot-image").src = response.image;
        byId("plot-image").hidden = false;
        byId("plot-placeholder").hidden = true;
        setMessage("plot-message", "График построен", "success");
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
byId("evaluate-button").addEventListener("click", evaluateExpression);
byId("expression-input").addEventListener("keydown", event => {
    if (event.key === "Enter") evaluateExpression();
});
byId("load-csv").addEventListener("click", loadCsv);
byId("plot-dataset").addEventListener("change", updatePlotColumns);
byId("render-plot").addEventListener("click", renderPlot);

document.addEventListener("pywebviewready", initialize);

if (window.pywebview?.api) {
    initialize();
}
