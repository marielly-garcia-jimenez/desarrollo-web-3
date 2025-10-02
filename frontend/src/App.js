import { useEffect, useState } from "react";
import "./App.css";

// URL base del backend, usa el puerto expuesto por docker-compose (8089)
const API_BASE_URL = "http://localhost:8089";

function App() {
  const [numbers, setNumbers] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingResult, setLoadingResult] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Filtros para el historial
  const [opFilter, setOpFilter] = useState("all");
  const [sortBy, setSortBy] = useState("date");
  const [sortOrder, setSortOrder] = useState("desc");

  // Efecto: Carga el historial al montar el componente
  useEffect(() => {
    fetchHistory();
  }, []);

  // Función de utilidad para convertir el string de entrada en array de números
  const parseNumbers = (str) => {
    const parts = str
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
      .map((n) => Number(n));

    if (parts.some((n) => Number.isNaN(n))) {
      throw new Error("Por favor ingresa sólo números separados por coma.");
    }
    if (parts.length < 2) {
      throw new Error("Se requieren al menos 2 números.");
    }
    return parts;
  };

  // Función principal para manejar las operaciones (POST)
  const handleOperation = async (op) => {
    setErrorMsg("");
    setResult(null);

    try {
      // Validar y parsear la entrada de N números
      const nums = parseNumbers(numbers);
      setLoadingResult(true);

      // Endpoint: /calculator/sum, /calculator/subtract, etc.
      const endpoint = op;

      const res = await fetch(`${API_BASE_URL}/calculator/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ numbers: nums }),
      });

      const data = await res.json();

      if (!res.ok) {
        // Manejo de errores 400, 403, 422 del backend (división por cero, negativos, etc.)
        const errDetail = data.detail || data.error || data;
        const readable =
          typeof errDetail === "string" ? errDetail : JSON.stringify(errDetail);
        setErrorMsg(readable);
      } else {
        setResult(data);
        // Actualizar historial tras operación exitosa
        fetchHistory();
      }
    } catch (err) {
      // Manejo de errores de red o errores de validación de parseNumbers
      setErrorMsg(err.message || String(err));
    } finally {
      setLoadingResult(false);
    }
  };

  // Función para obtener el historial con filtros (GET)
  const fetchHistory = async (options = {}) => {
    setLoadingHistory(true);
    setErrorMsg("");

    try {
      // Aplicar filtros o usar los filtros actuales del estado
      const op = options.opFilter ?? opFilter;
      const sb = options.sortBy ?? sortBy;
      const so = options.sortOrder ?? sortOrder;

      const params = new URLSearchParams();
      if (op && op !== "all") params.append("operation", op);
      params.append("sort_by", sb);
      params.append("sort_order", so);

      // Endpoint: /calculator/history?operation=...&sort_by=...
      const res = await fetch(
        `${API_BASE_URL}/calculator/history?${params.toString()}`
      );
      const data = await res.json();

      if (!res.ok) {
        setErrorMsg(data.detail || JSON.stringify(data));
      } else {
        setHistory(Array.isArray(data.history) ? data.history : []);
      }
    } catch (err) {
      // Error de red al intentar obtener el historial
      setErrorMsg("Error al conectar con el historial: " + (err.message || String(err)));
    } finally {
      setLoadingHistory(false);
    }
  };

  const onApplyFilters = () => {
    fetchHistory({ opFilter, sortBy, sortOrder });
  };

  return (
    <div className="container">
      <header>
        <h1>🧮 Calculadora - Proyecto Avanzado</h1>
        <p>Ingresa **dos o más** números separados por coma, luego elige la operación.</p>
      </header>
      
      <main>
        {/* Sección de Calculadora */}
        <section className="card input-card">
          <input
            type="text"
            placeholder="Ej: 12, 3, 4"
            value={numbers}
            onChange={(e) => setNumbers(e.target.value)}
            aria-label="Números separados por coma"
          />

          <div className="buttons">
            <button onClick={() => handleOperation("sum")} disabled={loadingResult}>
              ➕ Sumar
            </button>
            <button onClick={() => handleOperation("subtract")} disabled={loadingResult}>
              ➖ Restar
            </button>
            <button onClick={() => handleOperation("multiply")} disabled={loadingResult}>
              ✖ Multiplicar
            </button>
            <button onClick={() => handleOperation("divide")} disabled={loadingResult}>
              ➗ Dividir
            </button>
          </div>

          {loadingResult && <div className="info">Procesando...</div>}

          {errorMsg && (
            <div className="error">
              <strong>Error:</strong> {errorMsg}
            </div>
          )}

          {result && (
            <div className="result-card">
              <h3>Resultado</h3>
              <div className="result-body">
                <div>
                  <strong>Operación:</strong> {result.operation}
                </div>
                <div>
                  <strong>Números:</strong>{" "}
                  {Array.isArray(result.numbers)
                    ? result.numbers.join(", ")
                    : ""}
                </div>
                <div className="big-result">{result.result}</div>
              </div>
            </div>
          )}
        </section>

        {/* Sección de Historial */}
        <section className="card history-card">
          <div className="history-controls">
            <div className="control-row">
              <label>Filtro:</label>
              <select
                value={opFilter}
                onChange={(e) => setOpFilter(e.target.value)}
              >
                <option value="all">Todos</option>
                <option value="sum">SUM</option>
                <option value="subtract">SUBTRACT</option>
                <option value="multiplication">MULTIPLICATION</option>
                <option value="division">DIVISION</option>
              </select>

              <label>Ordenar por:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="date">Fecha</option>
                <option value="result">Resultado</option>
              </select>

              <label>Orden:</label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
              >
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
              </select>

              <button className="small" onClick={onApplyFilters} disabled={loadingHistory}>
                Aplicar
              </button>
            </div>
            {/* Se agrega un botón de refrescar para que sea más claro recargar el historial */}
            <button className="small refresh-btn" onClick={fetchHistory} disabled={loadingHistory}>
                Refrescar Historial
            </button>
          </div>

          <h3>📜 Historial de Operaciones</h3>

          {loadingHistory ? (
            <div className="info">Cargando historial...</div>
          ) : history.length === 0 ? (
            <div className="info">No hay operaciones registradas.</div>
          ) : (
            <ul className="history-list">
              {history.map((h, i) => (
                <li key={i} className="history-item">
                  <div className="history-main">
                    <span className="op">{h.operation?.toUpperCase()}</span>
                    <span className="nums">
                      {Array.isArray(h.numbers) ? h.numbers.join(", ") : ""}
                    </span>
                    <span className="res">= {h.result}</span>
                  </div>
                  <div className="history-meta">{h.date}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>

      <footer>
        <small>
          API: {API_BASE_URL} — si se pudo.
        </small>
      </footer>
    </div>
  );
}

export default App;
