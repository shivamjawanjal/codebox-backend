import './App.css';
import { useEffect, useState } from "react";
import Editor from '@monaco-editor/react';

function App() {

  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");

  const submitCode = () => {
    console.log("Code Submitted:", code);
  }

  useEffect(() => {
    console.log(code);
  }, [code]);

  return (
    <div className='App'>

      <button
        style={{
          background: language === "python" ? "black" : "white",
          color: language === "python" ? "white" : "black",
        }}
        onClick={() => setLanguage("python")}
      >
        Python
      </button>

      <button
        style={{
          background: language === "java" ? "black" : "white",
          color: language === "java" ? "white" : "black",
        }}
        onClick={() => setLanguage("java")}
      >
        Java
      </button>

      <button
        style={{
          background: language === "cpp" ? "black" : "white",
          color: language === "cpp" ? "white" : "black",
        }}
        onClick={() => setLanguage("cpp")}
      >
        CPP
      </button>

      <button onClick={submitCode}>Submit</button>

      <Editor
        height="90vh"
        theme="vs-dark"
        language={language}
        value={code}
        onChange={(value) => setCode(value)}
      />

    </div>
  );
}

export default App;
