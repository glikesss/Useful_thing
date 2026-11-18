const byId = (id) => document.getElementById(id);

let api = null;
let currentState = null;
let plotCurves = [];
let plotGraphs = [{id: 1, title: "График 1", curves: [], image: null}];
let activePlotGraphId = 1;
let nextPlotGraphId = 2;
let datasetsExpanded = false;
let formulaApplyTimer = null;
let formulaApplyRequest = 0;
let expressionTimer = null;
let expressionRequest = 0;

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

function formulaSourceToLatex(source) {
    // Convert common engine syntax into editable LaTeX for MathLive.
    let value = String(source || "").trim();
    value = value.replace(/\b(sqrt|sin|cos|tan|arcsin|arccos|arctan|sinh|cosh|tanh|ln|log|exp)\s*\(/g,
        (_, name) => "\\" + name + "(");
    value = value.replace(/\bpi\b/g, "\\pi").replace(/\binfinity\b/g, "\\infty");
    value = value.replace(/\*/g, "\\cdot ");
    return value;
}

function formulaMathToSource(mathfield) {
    let source = typeof mathfield.getValue === "function"
        ? mathfield.getValue("ascii-math").trim()
        : mathfield.value.trim();

    // Keep named data-access functions as ordinary engine identifiers.
    source = source.replace(/\\(?:operatorname|mathrm|text)\s*\{\s*file\s*\}/g, "file");
    return source;
}

function renderFormulaEditor(lines = [], formulas = []) {
    const container = byId("formula-editor-list");
    container.replaceChildren();
    const rows = lines.length ? lines : [""];

    rows.forEach((line, index) => {
        const item = document.createElement("div");
        item.className = "formula-row";

        const number = document.createElement("span");
        number.className = "formula-row-number";
        number.textContent = String(index + 1);

        const input = document.createElement("math-field");
        input.className = "formula-row-input";
        input.setAttribute("aria-label", "Формула " + (index + 1));
        input.setAttribute("math-virtual-keyboard-policy", "manual");
        input.setAttribute("smart-mode", "");
        input.setAttribute("placeholder", "Введите формулу…");
        input.value = formulaSourceToLatex(line);

        input.addEventListener("input", () => scheduleFormulaApply());
        input.addEventListener("keydown", event => {
            if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                // Always consume vertical navigation, including at the first/last row,
                // to prevent the embedded webview's boundary key sound.
                event.preventDefault();
                event.stopPropagation();
                const targetIndex = index + (event.key === "ArrowUp" ? -1 : 1);
                const target = container.children[targetIndex]?.querySelector(".formula-row-input");
                if (target) {
                    target.focus();
                    target.executeCommand(event.key === "ArrowUp"
                        ? "moveToMathfieldEnd"
                        : "moveToMathfieldStart");
                }
            } else if (event.key === "Enter" && !event.ctrlKey && !event.shiftKey) {
                event.preventDefault();
                addFormulaLine(index + 1);
            } else if (event.key === "Enter" && event.ctrlKey) {
                event.preventDefault();
                applyFormulas();
            } else if (event.key === "Backspace" && !formulaMathToSource(input) &&
                getFormulaLines().length > 1) {
                event.preventDefault();
                const current = getFormulaLines();
                current.splice(index, 1);
                renderFormulaEditor(current, currentState?.formulas || []);
                scheduleFormulaApply();
                const target = container.children[Math.max(0, index - 1)]?.querySelector(".formula-row-input");
                target?.focus();
            }
        });

        const remove = document.createElement("button");
        remove.className = "formula-row-remove";
        remove.type = "button";
        remove.title = "Удалить строку";
        remove.setAttribute("aria-label", "Удалить строку " + (index + 1));
        remove.textContent = "×";
        remove.addEventListener("click", () => {
            const current = getFormulaLines();
            current.splice(index, 1);
            renderFormulaEditor(current, currentState?.formulas || []);
            if (!current.length) renderFormulaEditor([""], currentState?.formulas || []);
            scheduleFormulaApply();
        });

        const result = document.createElement("span");
        result.className = "formula-row-result";
        result.hidden = true;

        item.append(number, input, remove, result);
        container.appendChild(item);
    });

    const importedArrays = (currentState?.variables || [])
        .filter(variable => variable.imported && variable.array_preview);
    for (const variable of importedArrays) {
        const preview = variable.array_preview;
        const values = preview.values.map(value =>
            typeof value === "number" ? Number(value.toPrecision(6)).toString() : String(value)
        );
        const suffix = preview.size > preview.values.length ? ", …" : "";
        const row = document.createElement("div");
        row.className = "formula-row imported-array-row";

        const marker = document.createElement("span");
        marker.className = "formula-row-number";
        marker.textContent = "↳";

        const expression = document.createElement("span");
        expression.className = "imported-array-expression";
        expression.textContent = `${variable.name} = [ ${values.join(", ")}${suffix} ]`;

        const meta = document.createElement("span");
        meta.className = "formula-row-result array-preview";
        meta.textContent = `${preview.size} элементов · ${preview.shape.join(" × ")}`;

        row.append(marker, expression, meta);
        container.appendChild(row);
    }
}

function getFormulaLines() {
    return Array.from(document.querySelectorAll(".formula-row-input"))
        .map(formulaMathToSource)
        .filter(Boolean);
}

function scheduleFormulaApply() {
    clearTimeout(formulaApplyTimer);
    const requestId = ++formulaApplyRequest;
    formulaApplyTimer = setTimeout(() => {
        if (requestId === formulaApplyRequest) applyFormulas(true);
    }, 500);
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

function updateArrayImportControls() {
    const datasetSelect = byId("array-import-dataset");
    const columnSelect = byId("array-import-column");
    const previousDataset = datasetSelect.value;
    const dataset = currentState?.datasets.find(item => item.name === previousDataset);
    datasetSelect.replaceChildren();
    addOption(datasetSelect, "", "Выберите набор");
    for (const item of currentState?.datasets || []) {
        addOption(datasetSelect, item.name, item.name);
    }
    datasetSelect.value = (currentState?.datasets || []).some(item => item.name === previousDataset)
        ? previousDataset
        : (currentState?.datasets?.[0]?.name || "");
    columnSelect.replaceChildren();
    const selected = currentState?.datasets.find(item => item.name === datasetSelect.value);
    if (!selected || !selected.numeric_columns.length) {
        addOption(columnSelect, "", "Нет числовых столбцов");
        columnSelect.disabled = true;
        byId("import-column-array").disabled = true;
        return;
    }
    addOption(columnSelect, "", "Выберите столбец");
    for (const column of selected.numeric_columns) addOption(columnSelect, column, column);
    columnSelect.disabled = false;
    byId("import-column-array").disabled = true;
}

function updateArrayImportColumns() {
    const dataset = currentState?.datasets.find(item => item.name === byId("array-import-dataset").value);
    const select = byId("array-import-column");
    select.replaceChildren();
    if (!dataset || !dataset.numeric_columns.length) {
        addOption(select, "", "Нет числовых столбцов");
        select.disabled = true;
        byId("import-column-array").disabled = true;
        return;
    }
    addOption(select, "", "Выберите столбец");
    for (const column of dataset.numeric_columns) addOption(select, column, column);
    select.disabled = false;
    byId("import-column-array").disabled = true;
}

async function importColumnArray() {
    const dataset = byId("array-import-dataset").value;
    const column = byId("array-import-column").value;
    const name = byId("array-import-name").value.trim();
    if (!dataset || !column || !name) {
        setMessage("array-import-message", "Выберите набор, столбец и задайте имя массива", "error");
        return;
    }
    try {
        const response = await api.import_column_to_array(dataset, column, name);
        if (!response.ok) {
            setMessage("array-import-message", response.error, "error");
            return;
        }
        renderState(response.state);
        byId("array-import-name").value = "";
        setMessage("array-import-message", response.message, "success");
    } catch (error) {
        setMessage("array-import-message", error.message, "error");
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


function updatePlotGroupControls() {
    const datasetSelect = byId("plot-group-datasets");
    const selectedNames = new Set(Array.from(datasetSelect.selectedOptions || []).map(option => option.value));
    datasetSelect.replaceChildren();
    for (const dataset of currentState?.datasets || []) {
        const option = document.createElement("option");
        option.value = dataset.name;
        option.textContent = dataset.name;
        option.selected = selectedNames.has(dataset.name);
        datasetSelect.appendChild(option);
    }
    datasetSelect.disabled = !(currentState?.datasets?.length);
    updatePlotGroupColumns();
}

function updatePlotGroupColumns() {
    const names = Array.from(byId("plot-group-datasets").selectedOptions).map(option => option.value);
    const datasets = (currentState?.datasets || []).filter(dataset => names.includes(dataset.name));
    const xSelect = byId("plot-group-x");
    const ySelect = byId("plot-group-y");
    const previousX = xSelect.value;
    const previousY = ySelect.value;
    const common = datasets.length
        ? datasets.map(dataset => dataset.numeric_columns)
            .reduce((shared, columns) => shared.filter(column => columns.includes(column)))
        : [];
    for (const select of [xSelect, ySelect]) {
        select.replaceChildren();
        addOption(select, "", common.length ? "Выберите столбец" : "Нет общих числовых столбцов");
        for (const column of common) addOption(select, column, column);
    }
    xSelect.value = common.includes(previousX) ? previousX : (common[0] || "");
    ySelect.value = common.includes(previousY) ? previousY : (common[1] || common[0] || "");
    xSelect.disabled = !common.length;
    ySelect.disabled = !common.length;
    byId("add-plot-group").disabled = datasets.length < 1 || common.length < 1;
}

function addPlotGroupCurves() {
    const names = Array.from(byId("plot-group-datasets").selectedOptions).map(option => option.value);
    const xColumn = byId("plot-group-x").value;
    const yColumn = byId("plot-group-y").value;
    if (!names.length || !xColumn || !yColumn) {
        setMessage("plot-message", "Выбери наборы данных и общие столбцы X/Y", "error");
        return;
    }
    if (plotCurves.some(curve => curve.source === "array")) {
        setMessage("plot-message", "На одном графике нельзя смешивать CSV и массивы. Очисти список кривых.", "error");
        return;
    }
    let added = 0;
    for (const name of names) {
        if (plotCurves.some(curve => curve.dataset_name === name && curve.x_column === xColumn && curve.y_column === yColumn)) continue;
        plotCurves.push({dataset_name: name, x_column: xColumn, y_column: yColumn, label: name + ": " + yColumn});
        added++;
    }
    renderCurveList();
    if (added) renderPlot();
    else setMessage("plot-message", "Такие кривые уже добавлены", "");
}

function updatePlotArrays() {
    const xSelect = byId("plot-array-x");
    const ySelect = byId("plot-array-y");
    const arrays = currentState?.arrays || [];
    xSelect.replaceChildren();
    ySelect.replaceChildren();

    if (!arrays.length) {
        addOption(xSelect, "", "Нет массивов");
        addOption(ySelect, "", "Нет массивов");
        xSelect.disabled = true;
        ySelect.disabled = true;
        byId("add-array-curve").disabled = true;
        return;
    }

    addOption(xSelect, "", "Выберите X");
    addOption(ySelect, "", "Выберите Y");
    for (const name of arrays) {
        addOption(xSelect, name, name);
        addOption(ySelect, name, name);
    }
    if (arrays.length > 1) ySelect.selectedIndex = 2;
    xSelect.disabled = false;
    ySelect.disabled = false;
    byId("add-array-curve").disabled = false;
}

function addArrayPlotCurve() {
    const xName = byId("plot-array-x").value;
    const yName = byId("plot-array-y").value;
    if (!xName || !yName) {
        setMessage("plot-message", "Выберите массивы X и Y", "error");
        return;
    }
    if (plotCurves.some(curve => curve.source !== "array") &&
        plotCurves.some(curve => curve.source === "array")) {
        setMessage("plot-message", "На одном графике нельзя смешивать CSV и массивы. Очистите список кривых.", "error");
        return;
    }
    const label = byId("plot-array-label").value.trim() || `${yName}(${xName})`;
    plotCurves.push({source: "array", x_name: xName, y_name: yName, label});
    byId("plot-array-label").value = "";
    renderCurveList();
    renderPlot();
}

function getActivePlotGraph() {
    return plotGraphs.find(graph => graph.id === activePlotGraphId) || plotGraphs[0];
}

function saveActivePlotGraph() {
    const graph = getActivePlotGraph();
    if (!graph) return;
    graph.curves = plotCurves;
    graph.title = byId("plot-title").value.trim() || graph.title;
    const image = byId("plot-image");
    graph.image = !image.hidden && image.src ? image.src : graph.image;
}

function renderPlotTabs() {
    const container = byId("plot-tabs");
    container.replaceChildren();
    plotGraphs.forEach(graph => {
        const tab = document.createElement("div");
        tab.className = "plot-tab" + (graph.id === activePlotGraphId ? " active" : "");
        const select = document.createElement("button");
        select.type = "button";
        select.className = "plot-tab-select";
        select.setAttribute("role", "tab");
        select.setAttribute("aria-selected", String(graph.id === activePlotGraphId));
        select.textContent = graph.title || "Без названия";
        select.addEventListener("click", () => activatePlotGraph(graph.id));
        tab.appendChild(select);
        if (plotGraphs.length > 1) {
            const close = document.createElement("button");
            close.type = "button";
            close.className = "plot-tab-close";
            close.textContent = "×";
            close.title = "Закрыть график";
            close.setAttribute("aria-label", "Закрыть " + graph.title);
            close.addEventListener("click", event => {
                event.stopPropagation();
                removePlotGraph(graph.id);
            });
            tab.appendChild(close);
        }
        container.appendChild(tab);
    });
}

function activatePlotGraph(id) {
    if (id === activePlotGraphId) return;
    saveActivePlotGraph();
    const graph = plotGraphs.find(item => item.id === id);
    if (!graph) return;
    activePlotGraphId = id;
    plotCurves = graph.curves;
    byId("plot-title").value = graph.title;
    const image = byId("plot-image");
    if (graph.image) {
        image.src = graph.image;
        image.hidden = false;
        byId("export-plot-png").disabled = false;
        byId("export-plot-pdf").disabled = false;
        byId("plot-placeholder").hidden = true;
    } else {
        image.removeAttribute("src");
        image.hidden = true;
        byId("export-plot-png").disabled = true;
        byId("export-plot-pdf").disabled = true;
        byId("plot-placeholder").hidden = false;
    }
    renderCurveList();
    renderPlotTabs();
    setMessage("plot-message", graph.image ? "Открыт сохранённый график" : "Новый график — добавьте кривые", "");
}

function addPlotGraph() {
    saveActivePlotGraph();
    const id = nextPlotGraphId++;
    plotGraphs.push({id, title: "График " + id, curves: [], image: null});
    activatePlotGraph(id);
}

function removePlotGraph(id) {
    if (plotGraphs.length <= 1) return;
    saveActivePlotGraph();
    const index = plotGraphs.findIndex(graph => graph.id === id);
    if (index < 0) return;
    plotGraphs.splice(index, 1);
    if (activePlotGraphId === id) {
        const next = plotGraphs[Math.min(index, plotGraphs.length - 1)];
        activePlotGraphId = next.id;
        plotCurves = next.curves;
        byId("plot-title").value = next.title;
        const image = byId("plot-image");
        if (next.image) {
            image.src = next.image;
            image.hidden = false;
            byId("export-plot-png").disabled = false;
            byId("export-plot-pdf").disabled = false;
            byId("plot-placeholder").hidden = true;
        } else {
            image.removeAttribute("src");
            image.hidden = true;
            byId("export-plot-png").disabled = true;
            byId("export-plot-pdf").disabled = true;
            byId("plot-placeholder").hidden = false;
        }
        renderCurveList();
    }
    renderPlotTabs();
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
        label.textContent = curve.source === "array"
            ? `${curve.label} · массивы (${curve.x_name}, ${curve.y_name})`
            : `${curve.label} · ${curve.dataset_name} (${curve.x_column}, ${curve.y_column})`;

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
    if (plotCurves.some(curve => curve.source === "array")) {
        setMessage("plot-message", "На одном графике нельзя смешивать CSV и массивы. Очистите список кривых.", "error");
        return;
    }
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
    renderPlot();
}

function renderDatasets(datasets) {
    const container = byId("datasets-list");
    const plotSelect = byId("plot-dataset");
    const tableSelect = byId("table-dataset");
    const previousPlot = plotSelect.value;
    const previousTable = tableSelect.value;

    container.replaceChildren();
    plotSelect.replaceChildren();
    tableSelect.replaceChildren();

    if (!datasets.length) {
        container.textContent = "CSV-файлы ещё не загружены";
        container.className = "dataset-list empty";
        addOption(plotSelect, "", "Нет данных");
        addOption(tableSelect, "", "Нет данных");
        plotSelect.disabled = true;
        tableSelect.disabled = true;
        byId("refresh-table").disabled = true;
        byId("export-table-xlsx").disabled = true;
        updatePlotColumns();
        updatePlotGroupControls();
        renderCurveList();
        renderTablePlaceholder("Загрузите CSV для просмотра таблицы");
        return;
    }

    container.className = "dataset-list";
    const toggle = byId("toggle-datasets");
    toggle.hidden = true;
    plotSelect.disabled = false;
    tableSelect.disabled = false;
    byId("refresh-table").disabled = false;

    addOption(plotSelect, "", "Выберите набор");
    addOption(tableSelect, "", "Выберите набор");

    datasets.forEach((dataset, index) => {
        const item = document.createElement("div");
        item.className = "dataset-item";

        const number = document.createElement("span");
        number.className = "dataset-number";
        number.textContent = String(index + 1).padStart(2, "0");

        const details = document.createElement("div");
        details.className = "dataset-item-details";
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
        item.append(number, details, actions);
        container.appendChild(item);

        addOption(plotSelect, dataset.name, dataset.name);
        addOption(tableSelect, dataset.name, dataset.name);
    });

    plotSelect.value = datasets.some(item => item.name === previousPlot)
        ? previousPlot
        : datasets[0].name;

    tableSelect.value = datasets.some(item => item.name === previousTable)
        ? previousTable
        : datasets[0].name;
    byId("export-table-xlsx").disabled = !tableSelect.value;

    updatePlotColumns();
    updatePlotGroupControls();
    refreshTable();
}

function renderState(state, updateEditor = false, preserveFormulaEditor = false) {
    currentState = state;

    if (!preserveFormulaEditor) {
        if (updateEditor || !byId("formula-editor-list").children.length) {
            renderFormulaEditor(state.lines || [], state.formulas || []);
        } else {
            renderFormulaEditor(getFormulaLines(), state.formulas || []);
        }
    }
    renderVariables(state.variables);
    renderFunctions(state.functions);
    updatePlotArrays();
    renderDatasets(state.datasets);
    updateArrayImportControls();
}

async function refreshState(updateEditor = false) {
    const state = await api.get_state();
    renderState(state, updateEditor);
}

function isDefinitionLine(source) {
    let depth = 0;
    for (let i = 0; i < source.length; i++) {
        const char = source[i];
        if ("([{".includes(char)) depth++;
        else if (")]}".includes(char)) depth--;
        else if (char === "=" && depth === 0) {
            const before = source[i - 1] || "";
            const after = source[i + 1] || "";
            if (!"<>!=".includes(before) && after !== "=") return true;
        }
    }
    return false;
}

async function applyFormulas(automatic = false) {
    clearTimeout(formulaApplyTimer);
    const requestId = ++formulaApplyRequest;
    const lines = getFormulaLines();
    const definitions = lines.filter(isDefinitionLine);
    const expressions = lines.filter(line => !isDefinitionLine(line));

    try {
        const response = await api.set_lines(definitions);
        if (requestId !== formulaApplyRequest) return;

        if (!response.ok) {
            setMessage("formula-message", response.error, "error");
            return;
        }

        renderState(response.state, false, true);
        const rows = Array.from(document.querySelectorAll(".formula-row:not(.imported-array-row)"))
            .filter(row => formulaMathToSource(row.querySelector(".formula-row-input")));
        let expressionIndex = 0;

        for (let i = 0; i < lines.length; i++) {
            const result = rows[i]?.querySelector(".formula-row-result");
            if (!result) continue;

            if (isDefinitionLine(lines[i])) {
                const name = lines[i].match(/^\\s*([A-Za-z_]\\w*)\\s*=/)?.[1];
                const variable = currentState?.variables?.find(item => item.name === name);
                const preview = variable?.array_preview;
                if (preview) {
                    const values = preview.values.map(value =>
                        typeof value === "number" ? Number(value.toPrecision(6)).toString() : String(value)
                    );
                    const suffix = preview.size > preview.values.length ? ", …" : "";
                    const shape = preview.shape.join(" × ");
                    result.textContent = `[ ${values.join(", ")}${suffix} ] · ${preview.size} элементов · ${shape}`;
                    result.hidden = false;
                    result.classList.add("array-preview");
                } else {
                    result.hidden = true;
                    result.textContent = "";
                    result.classList.remove("array-preview");
                }
                result.closest(".formula-row")?.classList.remove("has-error");
                continue;
            }

            const expression = expressions[expressionIndex++];
            if (!expression) continue;

            try {
                const evaluated = await api.evaluate(expression);
                if (requestId !== formulaApplyRequest) return;
                result.textContent = evaluated.ok ? "= " + evaluated.result : evaluated.error;
                result.hidden = false;
                result.classList.toggle("error", !evaluated.ok);
                result.closest(".formula-row")?.classList.toggle("has-error", !evaluated.ok);
            } catch (error) {
                result.textContent = error.message;
                result.hidden = false;
                result.classList.add("error");
                result.closest(".formula-row")?.classList.add("has-error");
            }
        }

        setMessage("formula-message", automatic ? "Изменения применены" : response.message, "success");
    } catch (error) {
        if (requestId === formulaApplyRequest) {
            setMessage("formula-message", error.message, "error");
        }
    }
}
function addFormulaLine(afterIndex = null) {
    const lines = getFormulaLines();
    const insertAt = afterIndex === null ? lines.length : afterIndex;
    lines.splice(insertAt, 0, "");
    renderFormulaEditor(lines, currentState?.formulas || []);
    scheduleFormulaApply();
    const input = byId("formula-editor-list").children[insertAt]?.querySelector(".formula-row-input");
    input?.focus();
}

function scheduleExpressionEvaluation() {
    clearTimeout(expressionTimer);
    const requestId = ++expressionRequest;
    expressionTimer = setTimeout(() => {
        if (requestId === expressionRequest) evaluateExpression(true);
    }, 350);
}

async function evaluateExpression(automatic = false) {
    clearTimeout(expressionTimer);
    const requestId = ++expressionRequest;
    const expression = byId("expression-input").value.trim();

    if (!expression) {
        byId("evaluation-result").textContent = "Ожидание выражения...";
        setMessage("evaluation-message", "");
        return;
    }

    try {
        const response = await api.evaluate(expression);
        if (requestId !== expressionRequest || expression !== byId("expression-input").value.trim()) return;

        if (!response.ok) {
            byId("evaluation-result").textContent = "—";
            setMessage("evaluation-message", response.error, "error");
            return;
        }

        byId("evaluation-result").textContent = response.result;
        setMessage("evaluation-message", automatic ? "Обновлено" : "Готово", "success");
    } catch (error) {
        if (requestId === expressionRequest) setMessage("evaluation-message", error.message, "error");
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

async function exportTable(fileFormat) {
    const name = byId("table-dataset").value;
    if (!name) {
        setMessage("table-message", "Выберите набор данных", "error");
        return;
    }
    try {
        const response = await api.select_export_table_file(name, fileFormat);
        if (response.cancelled) return;
        if (!response.ok) {
            setMessage("table-message", response.error, "error");
            return;
        }
        setMessage("table-message", response.message, "success");
    } catch (error) {
        setMessage("table-message", error.message, "error");
    }
}

async function exportPlot(fileFormat) {
    const graph = getActivePlotGraph();
    if (!graph || !graph.curves.length) {
        setMessage("plot-message", "Сначала постройте график", "error");
        return;
    }
    try {
        const title = byId("plot-title").value.trim() || graph.title || "График";
        const arrayCurves = graph.curves.every(curve => curve.source === "array");
        const csvCurves = graph.curves.every(curve => curve.source !== "array");
        if (!arrayCurves && !csvCurves) {
            setMessage("plot-message", "На одном графике нельзя смешивать CSV и массивы", "error");
            return;
        }
        const response = await api.select_export_plot_file(
            title,
            graph.curves.map(({source, dataset_name, x_column, y_column, x_name, y_name, label}) =>
                ({source, dataset_name, x_column, y_column, x_name, y_name, label})),
            fileFormat,
            arrayCurves ? "array" : "csv",
            byId("plot-legend-visible").checked,
            byId("plot-legend-position").value,
            getPlotSmoothing(),
        );
        if (response.cancelled) return;
        if (!response.ok) {
            setMessage("plot-message", response.error, "error");
            return;
        }
        setMessage("plot-message", response.message, "success");
    } catch (error) {
        setMessage("plot-message", error.message, "error");
    }
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

    const title = byId("plot-title").value.trim() || getActivePlotGraph().title;

    try {
        const arrayCurves = plotCurves.every(curve => curve.source === "array");
        const csvCurves = plotCurves.every(curve => curve.source !== "array");
        if (!arrayCurves && !csvCurves) {
            setMessage("plot-message", "Нельзя смешивать CSV и массивы на одном графике", "error");
            return;
        }
        const legendVisible = byId("plot-legend-visible").checked;
        const legendPosition = byId("plot-legend-position").value;
        const response = arrayCurves
            ? await api.render_plot_array_curves(
                plotCurves.map(({x_name, y_name, label}) => ({x_name, y_name, label})),
                title,
                legendVisible,
                legendPosition,
                getPlotSmoothing(),
            )
            : await api.render_plot_curves(
                plotCurves,
                title,
                legendVisible,
                legendPosition,
                getPlotSmoothing(),
            );

        if (!response.ok) {
            setMessage("plot-message", response.error, "error");
            return;
        }

        byId("plot-image").src = response.image;
        byId("plot-image").hidden = false;
        byId("export-plot-png").disabled = false;
        byId("export-plot-pdf").disabled = false;
        byId("plot-placeholder").hidden = true;
        const graph = getActivePlotGraph();
        graph.title = title;
        graph.image = response.image;
        graph.curves = plotCurves;
        renderPlotTabs();
        setMessage(
            "plot-message",
            `Построено кривых: ${response.curve_count}`,
            "success",
        );
    } catch (error) {
        setMessage("plot-message", error.message, "error");
    }
}

function getPlotSmoothing() {
    return {
        enabled: byId("plot-smoothing-enabled").checked,
        method: byId("plot-smoothing-method").value,
        window: Number.parseInt(byId("plot-smoothing-window").value, 10) || 5,
        polyorder: 2,
    };
}

function updatePlotSmoothingControls() {
    const enabled = byId("plot-smoothing-enabled").checked;
    byId("plot-smoothing-method").disabled = !enabled;
    byId("plot-smoothing-window").disabled = !enabled;
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
byId("clear-formulas").addEventListener("click", async () => {
    renderFormulaEditor([""]);
    await applyFormulas();
});
byId("add-formula-line").addEventListener("click", () => addFormulaLine());

byId("load-csv").addEventListener("click", loadCsv);
byId("toggle-datasets").addEventListener("click", () => {
    datasetsExpanded = !datasetsExpanded;
    renderDatasets(currentState?.datasets || []);
});
byId("plot-group-datasets").addEventListener("change", updatePlotGroupColumns);
byId("add-plot-group").addEventListener("click", addPlotGroupCurves);
byId("array-import-dataset").addEventListener("change", updateArrayImportColumns);
byId("array-import-column").addEventListener("change", () => {
    byId("import-column-array").disabled = !byId("array-import-column").value;
});
byId("import-column-array").addEventListener("click", importColumnArray);
byId("plot-dataset").addEventListener("change", updatePlotColumns);
byId("add-plot-curve").addEventListener("click", addPlotCurve);
byId("add-array-curve").addEventListener("click", addArrayPlotCurve);
byId("render-plot").addEventListener("click", renderPlot);
byId("plot-smoothing-enabled").addEventListener("change", updatePlotSmoothingControls);
byId("plot-smoothing-method").addEventListener("change", () => {
    const windowInput = byId("plot-smoothing-window");
    if (byId("plot-smoothing-method").value === "savgol") {
        windowInput.min = "3";
        if (Number(windowInput.value) % 2 === 0) windowInput.value = String(Number(windowInput.value) + 1);
    } else {
        windowInput.min = "1";
    }
});
byId("plot-smoothing-window").addEventListener("change", () => {
    const input = byId("plot-smoothing-window");
    let value = Math.max(Number(input.min) || 1, Math.floor(Number(input.value) || 5));
    if (byId("plot-smoothing-method").value === "savgol" && value % 2 === 0) value += 1;
    input.value = String(value);
});
byId("add-plot-tab").addEventListener("click", addPlotGraph);
byId("plot-title").addEventListener("input", () => {
    const graph = getActivePlotGraph();
    if (graph) {
        graph.title = byId("plot-title").value.trim() || ("График " + graph.id);
        renderPlotTabs();
    }
});
renderPlotTabs();
byId("table-dataset").addEventListener("change", refreshTable);
byId("refresh-table").addEventListener("click", refreshTable);
byId("export-plot-png").addEventListener("click", () => exportPlot("png"));
byId("export-plot-pdf").addEventListener("click", () => exportPlot("pdf"));
byId("export-table-xlsx").addEventListener("click", () => exportTable("xlsx"));
byId("table-dataset").addEventListener("change", () => {
    const enabled = Boolean(byId("table-dataset").value);
    byId("export-table-xlsx").disabled = !enabled;
});

window.addEventListener("pywebviewready", initialize);
if (window.pywebview?.api) initialize();



function initializeAppearance() {
    const root = document.documentElement;
    const themeSelect = byId("theme-select");
    const paletteSelect = byId("palette-select");
    const savedTheme = localStorage.getItem("mathlab-theme") || "dark";
    const savedPalette = localStorage.getItem("mathlab-palette") || "blue";
    const apply = () => {
        root.dataset.theme = themeSelect.value;
        root.dataset.palette = paletteSelect.value;
        localStorage.setItem("mathlab-theme", themeSelect.value);
        localStorage.setItem("mathlab-palette", paletteSelect.value);
    };
    themeSelect.value = ["dark", "light", "midnight"].includes(savedTheme) ? savedTheme : "dark";
    paletteSelect.value = ["blue", "violet", "emerald", "rose", "amber"].includes(savedPalette) ? savedPalette : "blue";
    themeSelect.addEventListener("change", apply);
    paletteSelect.addEventListener("change", apply);
    apply();
}
initializeAppearance();
