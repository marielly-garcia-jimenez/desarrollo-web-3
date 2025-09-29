import './App.css';
import React, { useState, useEffect } from "react";
function App() {
 const [a, setA] = useState("");
 const [b, setB] = useState("");
 const [resultado, setResultado] = useState(null);
 const [historial, setHistorial] = useState([]);
 const sumar = async () => {
 const res = await fetch(`http://localhost:8080/calculadora/sum?a=${a}&b=${b}`);
 const data = await res.json();
 setResultado(data.resultado);
 obtenerHistorial();
 };
 const obtenerHistorial = async () => {
 const res = await fetch("http://localhost:8080/calculadora/historial");
 const data = await res.json();
 setHistorial(data.historial);
 };
 useEffect(() => {
 obtenerHistorial();
 }, []);
 return (
 <div style={{ padding: 20 }}>
 <h1>Calculadora</h1>
 <input
 type="number"
 value={a}
 onChange={(e) => setA(e.target.value)}
 placeholder="Número Numero"
 />
 <input
 type="number"
 value={b}
 onChange={(e) => setB(e.target.value)}
 placeholder="Número Numero 2"
 />
 <button onClick={sumar}>Sumar</button>
 {resultado !== null && <h2>Resultado: {resultado}</h2>}
 <h3>Historial:</h3>
 <ul>
 {historial.map((op, i) => (
 <li key={i}>
 {op.a} + {op.b} = {op.resultado} ({op.date})
 </li>
 ))}
 </ul>
 </div>
 );
}
export default App;
