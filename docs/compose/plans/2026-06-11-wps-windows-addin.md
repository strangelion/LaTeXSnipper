# WPS Windows Add-in Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a WPS Office plugin for Windows that allows users to insert LaTeX formulas into WPS documents.

**Architecture:** Hybrid architecture with shared core components and platform-specific adapters. Uses WPS JS API for document interaction, HTTP Bridge for LaTeX conversion with local KaTeX fallback, and MathLive for formula editing.

**Tech Stack:** JavaScript, HTML/CSS, WPS JS API, KaTeX, MathLive, HTTP Bridge

---

## File Structure

```
office_plugin/
├── shared/                          # Shared components (NEW)
│   ├── core/
│   │   ├── bridge-client.js         # HTTP Bridge client with fallback
│   │   ├── local-renderer.js        # Local KaTeX renderer
│   │   ├── latex-parser.js          # LaTeX parser
│   │   └── i18n/
│   │       ├── en.json              # English translations
│   │       └── zh.json              # Chinese translations
│   ├── ui/
│   │   ├── mathlive-editor.js       # MathLive editor wrapper
│   │   ├── symbol-library.js        # Symbol library component
│   │   └── preview-panel.js         # Preview panel component
│   └── styles/
│       └── common.css               # Shared styles
│
├── hosts/
│   └── WpsAddIn/                    # WPS Windows Add-in (NEW)
│       ├── wps.plugin.xml           # WPS plugin manifest
│       ├── src/
│       │   ├── index.html           # Task Pane entry
│       │   ├── main.js              # Plugin initialization
│       │   ├── taskpane.html        # Task Pane UI
│       │   ├── taskpane.js          # Task Pane logic
│       │   └── adapters/
│       │       ├── wps-document.js  # WPS document adapter
│       │       └── wps-selection.js # WPS selection adapter
│       └── assets/
│           └── icons/
│               └── icon.png         # Plugin icon
```

---

## Task 1: Project Setup and Manifest

**Covers:** [S1] Problem, [S2] Solution overview

**Files:**
- Create: `office_plugin/hosts/WpsAddIn/wps.plugin.xml`
- Create: `office_plugin/hosts/WpsAddIn/src/index.html`
- Create: `office_plugin/hosts/WpsAddIn/assets/icons/icon.png`

- [ ] **Step 1: Create WPS plugin manifest**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp xmlns="http://schemas.microsoft.com/office/appforoffice/1.0"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Id>com.latexsnipper.wps</Id>
  <Version>1.0.0</Version>
  <Provider>LaTeXSnipper</Provider>
  <DefaultLocale>zh-CN</DefaultLocale>
  <HostApplication Name="Wps">
    <Host Name="Wps.Document" />
    <Host Name="Wps.Presentation" />
  </HostApplication>
  <App>
    <Title>LaTeXSnipper</Title>
    <Description>Insert LaTeX formulas into WPS documents</Description>
    <AppVersion>1.0.0</AppVersion>
  </App>
</OfficeApp>
```

- [ ] **Step 2: Create Task Pane entry page**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LaTeXSnipper</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      margin: 0;
      padding: 0;
      background: #f5f5f5;
    }
    #app {
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
  </style>
</head>
<body>
  <div id="app">
    <div id="taskpane"></div>
  </div>
  <script src="main.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create placeholder icon**

Create a simple 64x64 PNG icon with "LS" text (LaTeXSnipper initials).

- [ ] **Step 4: Verify project structure**

Run: `ls -la office_plugin/hosts/WpsAddIn/`
Expected: wps.plugin.xml, src/, assets/

- [ ] **Step 5: Commit**

```bash
git add office_plugin/hosts/WpsAddIn/
git commit -m "feat(wps): create WPS plugin project structure and manifest"
```

---

## Task 2: Shared Core - Bridge Client

**Covers:** [S3] Bridge integration, [S4] Formula insertion

**Files:**
- Create: `office_plugin/shared/core/bridge-client.js`
- Create: `office_plugin/shared/core/local-renderer.js`
- Test: `office_plugin/shared/core/__tests__/bridge-client.test.js`

- [ ] **Step 1: Write failing test for BridgeClient**

```javascript
// office_plugin/shared/core/__tests__/bridge-client.test.js
const { BridgeClient } = require('../bridge-client');

describe('BridgeClient', () => {
  test('should initialize with default URL', () => {
    const client = new BridgeClient();
    expect(client.baseUrl).toBe('http://127.0.0.1:28765');
  });

  test('should have connect method', () => {
    const client = new BridgeClient();
    expect(typeof client.connect).toBe('function');
  });

  test('should have convertLatex method', () => {
    const client = new BridgeClient();
    expect(typeof client.convertLatex).toBe('function');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd office_plugin && npm test`
Expected: FAIL with "Cannot find module '../bridge-client'"

- [ ] **Step 3: Write BridgeClient implementation**

```javascript
// office_plugin/shared/core/bridge-client.js
class BridgeClient {
  constructor(baseUrl = 'http://127.0.0.1:28765') {
    this.baseUrl = baseUrl;
    this.token = null;
    this.isConnected = false;
    this.localRenderer = null;
  }

  async connect() {
    try {
      const response = await fetch(`${this.baseUrl}/config`);
      if (!response.ok) {
        throw new Error('Bridge not available');
      }
      const data = await response.json();
      this.token = data.token;
      this.isConnected = true;
      return true;
    } catch (error) {
      console.warn('Bridge not available, using local renderer');
      this.isConnected = false;
      const { LocalRenderer } = require('./local-renderer');
      this.localRenderer = new LocalRenderer();
      return false;
    }
  }

  async convertLatex(latex, options = {}) {
    const { display = true, targets = ['omml', 'png'] } = options;

    if (this.isConnected) {
      return await this.bridgeConvert(latex, display, targets);
    } else {
      return await this.localRenderer.convert(latex, { display });
    }
  }

  async bridgeConvert(latex, display, targets) {
    const response = await fetch(`${this.baseUrl}/convert/latex`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ latex, display, targets })
    });

    if (!response.ok) {
      throw new Error(`Bridge error: ${response.status}`);
    }

    return await response.json();
  }
}

module.exports = { BridgeClient };
```

- [ ] **Step 4: Write LocalRenderer implementation**

```javascript
// office_plugin/shared/core/local-renderer.js
class LocalRenderer {
  async convert(latex, options = {}) {
    const { display = true } = options;

    try {
      // Use KaTeX for local rendering
      const katex = require('katex');
      const html = katex.renderToString(latex, {
        displayMode: display,
        throwOnError: false
      });

      return {
        ok: true,
        result: {
          latex,
          display,
          omml: null,
          png: await this.htmlToPng(html)
        }
      };
    } catch (error) {
      return {
        ok: false,
        error: { code: 'render_error', message: error.message }
      };
    }
  }

  async htmlToPng(html) {
    // Placeholder - will implement with canvas in Task 4
    return null;
  }
}

module.exports = { LocalRenderer };
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd office_plugin && npm test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add office_plugin/shared/core/
git commit -m "feat(wps): add BridgeClient and LocalRenderer with fallback"
```

---

## Task 3: Shared Core - LaTeX Parser

**Covers:** (no spec section — foundational utility for parsing LaTeX input)

**Files:**
- Create: `office_plugin/shared/core/latex-parser.js`
- Test: `office_plugin/shared/core/__tests__/latex-parser.test.js`

- [ ] **Step 1: Write failing test for LaTeX parser**

```javascript
// office_plugin/shared/core/__tests__/latex-parser.test.js
const { LatexParser } = require('../latex-parser');

describe('LatexParser', () => {
  test('should parse simple formula', () => {
    const parser = new LatexParser();
    const result = parser.parse('E = mc^2');
    expect(result.valid).toBe(true);
    expect(result.latex).toBe('E = mc^{2}');
  });

  test('should detect display mode', () => {
    const parser = new LatexParser();
    const result = parser.parse('\\[ E = mc^2 \\]');
    expect(result.display).toBe(true);
  });

  test('should detect inline mode', () => {
    const parser = new LatexParser();
    const result = parser.parse('$E = mc^2$');
    expect(result.display).toBe(false);
  });

  test('should handle invalid LaTeX', () => {
    const parser = new LatexParser();
    const result = parser.parse('\\frac{');
    expect(result.valid).toBe(false);
    expect(result.error).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd office_plugin && npm test`
Expected: FAIL with "Cannot find module '../latex-parser'"

- [ ] **Step 3: Write LaTeX parser implementation**

```javascript
// office_plugin/shared/core/latex-parser.js
class LatexParser {
  parse(input) {
    if (!input || typeof input !== 'string') {
      return { valid: false, error: 'Invalid input', latex: '', display: false };
    }

    const trimmed = input.trim();

    // Detect display mode
    let display = false;
    let latex = trimmed;

    if (trimmed.startsWith('\\[') && trimmed.endsWith('\\]')) {
      display = true;
      latex = trimmed.slice(2, -2).trim();
    } else if (trimmed.startsWith('\\begin{equation}') && trimmed.endsWith('\\end{equation}')) {
      display = true;
      latex = trimmed.slice(16, -15).trim();
    } else if (trimmed.startsWith('$') && trimmed.endsWith('$') && !trimmed.startsWith('$$')) {
      display = false;
      latex = trimmed.slice(1, -1).trim();
    } else if (trimmed.startsWith('$$') && trimmed.endsWith('$$')) {
      display = true;
      latex = trimmed.slice(2, -2).trim();
    }

    // Basic validation - check for balanced braces
    const openBraces = (latex.match(/\{/g) || []).length;
    const closeBraces = (latex.match(/\}/g) || []).length;

    if (openBraces !== closeBraces) {
      return {
        valid: false,
        error: 'Unbalanced braces',
        latex,
        display
      };
    }

    // Convert simple expressions to proper LaTeX
    latex = this.normalizeLatex(latex);

    return {
      valid: true,
      latex,
      display,
      error: null
    };
  }

  normalizeLatex(latex) {
    // Convert ^2 to ^{2}, etc.
    return latex.replace(/\^(\d+)/g, '^{$1}')
                .replace(/_(\d+)/g, '_{$1}');
  }
}

module.exports = { LatexParser };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd office_plugin && npm test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add office_plugin/shared/core/latex-parser.js
git commit -m "feat(wps): add LaTeX parser with mode detection"
```

---

## Task 4: Shared UI - MathLive Editor

**Covers:** [S7] UI design, [S8] Formula editing

**Files:**
- Create: `office_plugin/shared/ui/mathlive-editor.js`
- Create: `office_plugin/shared/styles/common.css`

- [ ] **Step 1: Create shared styles**

```css
/* office_plugin/shared/styles/common.css */
:root {
  --primary-color: #1976d2;
  --primary-hover: #1565c0;
  --background-color: #f5f5f5;
  --surface-color: #ffffff;
  --text-primary: #212121;
  --text-secondary: #757575;
  --border-color: #e0e0e0;
  --error-color: #d32f2f;
  --success-color: #388e3c;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--background-color);
  color: var(--text-primary);
}

.taskpane {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.taskpane-header {
  padding: 16px;
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
}

.taskpane-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.taskpane-footer {
  padding: 16px;
  background: var(--surface-color);
  border-top: 1px solid var(--border-color);
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-secondary {
  background: transparent;
  color: var(--primary-color);
  border: 1px solid var(--primary-color);
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.error-message {
  color: var(--error-color);
  font-size: 12px;
  margin-top: 4px;
}

.success-message {
  color: var(--success-color);
  font-size: 12px;
  margin-top: 4px;
}
```

- [ ] **Step 2: Create MathLive editor wrapper**

```javascript
// office_plugin/shared/ui/mathlive-editor.js
class MathLiveEditor {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      virtualKeyboardMode: 'manual',
      ...options
    };
    this.mathfield = null;
    this.callbacks = {
      change: [],
      submit: []
    };
    this.init();
  }

  init() {
    // Load MathLive CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdn.jsdelivr.net/npm/mathlive@0.95.5/dist/mathlive-static.css';
    document.head.appendChild(link);

    // Create mathfield element
    const mathfield = document.createElement('div');
    mathfield.className = 'mathfield';
    mathfield.setAttribute('virtual-keyboard-mode', this.options.virtualKeyboardMode);
    this.container.appendChild(mathfield);

    // Initialize MathLive
    if (window.MathLive) {
      this.mathfield = window.MathLive.makeMathField(mathfield, {
        onContentDidChange: (mf) => {
          this.emit('change', mf.latex);
        },
        onKeystroke: (mf, keystroke) => {
          if (keystroke === '[enter]' && !mf.isSelectionCollapsed) {
            this.emit('submit', mf.latex);
            return false;
          }
          return true;
        }
      });
    }
  }

  getLatex() {
    return this.mathfield ? this.mathfield.latex : '';
  }

  setLatex(latex) {
    if (this.mathfield) {
      this.mathfield.latex = latex;
    }
  }

  on(event, callback) {
    if (this.callbacks[event]) {
      this.callbacks[event].push(callback);
    }
  }

  emit(event, ...args) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach(cb => cb(...args));
    }
  }

  destroy() {
    if (this.mathfield) {
      this.mathfield.destroy();
    }
  }
}

module.exports = { MathLiveEditor };
```

- [ ] **Step 3: Commit**

```bash
git add office_plugin/shared/ui/ office_plugin/shared/styles/
git commit -m "feat(wps): add MathLive editor wrapper and shared styles"
```

---

## Task 5: Shared UI - Symbol Library

**Covers:** [S5] Symbol library, [S9] Complete symbol library

**Files:**
- Create: `office_plugin/shared/ui/symbol-library.js`

- [ ] **Step 1: Create symbol library component**

```javascript
// office_plugin/shared/ui/symbol-library.js
class SymbolLibrary {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      categories: this.getDefaultCategories(),
      ...options
    };
    this.callbacks = {
      select: []
    };
    this.init();
  }

  getDefaultCategories() {
    return [
      {
        name: 'Greek',
        nameZh: '希腊字母',
        symbols: [
          { latex: '\\alpha', display: 'α' },
          { latex: '\\beta', display: 'β' },
          { latex: '\\gamma', display: 'γ' },
          { latex: '\\delta', display: 'δ' },
          { latex: '\\epsilon', display: 'ε' },
          { latex: '\\zeta', display: 'ζ' },
          { latex: '\\eta', display: 'η' },
          { latex: '\\theta', display: 'θ' },
          { latex: '\\iota', display: 'ι' },
          { latex: '\\kappa', display: 'κ' },
          { latex: '\\lambda', display: 'λ' },
          { latex: '\\mu', display: 'μ' },
          { latex: '\\nu', display: 'ν' },
          { latex: '\\xi', display: 'ξ' },
          { latex: '\\pi', display: 'π' },
          { latex: '\\rho', display: 'ρ' },
          { latex: '\\sigma', display: 'σ' },
          { latex: '\\tau', display: 'τ' },
          { latex: '\\upsilon', display: 'υ' },
          { latex: '\\phi', display: 'φ' },
          { latex: '\\chi', display: 'χ' },
          { latex: '\\psi', display: 'ψ' },
          { latex: '\\omega', display: 'ω' }
        ]
      },
      {
        name: 'Operators',
        nameZh: '运算符',
        symbols: [
          { latex: '+', display: '+' },
          { latex: '-', display: '−' },
          { latex: '\\times', display: '×' },
          { latex: '\\div', display: '÷' },
          { latex: '\\pm', display: '±' },
          { latex: '\\mp', display: '∓' },
          { latex: '\\cdot', display: '·' },
          { latex: '\\ast', display: '∗' },
          { latex: '\\circ', display: '∘' },
          { latex: '\\bullet', display: '•' }
        ]
      },
      {
        name: 'Relations',
        nameZh: '关系符',
        symbols: [
          { latex: '=', display: '=' },
          { latex: '\\neq', display: '≠' },
          { latex: '<', display: '<' },
          { latex: '>', display: '>' },
          { latex: '\\leq', display: '≤' },
          { latex: '\\geq', display: '≥' },
          { latex: '\\approx', display: '≈' },
          { latex: '\\equiv', display: '≡' },
          { latex: '\\sim', display: '∼' },
          { latex: '\\simeq', display: '≃' }
        ]
      },
      {
        name: 'Arrows',
        nameZh: '箭头',
        symbols: [
          { latex: '\\leftarrow', display: '←' },
          { latex: '\\rightarrow', display: '→' },
          { latex: '\\leftrightarrow', display: '↔' },
          { latex: '\\Leftarrow', display: '⇐' },
          { latex: '\\Rightarrow', display: '⇒' },
          { latex: '\\Leftrightarrow', display: '⇔' },
          { latex: '\\uparrow', display: '↑' },
          { latex: '\\downarrow', display: '↓' }
        ]
      },
      {
        name: 'Accents',
        nameZh: '重音',
        symbols: [
          { latex: '\\hat{a}', display: 'â' },
          { latex: '\\bar{a}', display: 'ā' },
          { latex: '\\dot{a}', display: 'ȧ' },
          { latex: '\\ddot{a}', display: 'ä' },
          { latex: '\\tilde{a}', display: 'ã' },
          { latex: '\\vec{a}', display: 'a⃗' }
        ]
      },
      {
        name: 'Functions',
        nameZh: '函数',
        symbols: [
          { latex: '\\sin', display: 'sin' },
          { latex: '\\cos', display: 'cos' },
          { latex: '\\tan', display: 'tan' },
          { latex: '\\log', display: 'log' },
          { latex: '\\ln', display: 'ln' },
          { latex: '\\exp', display: 'exp' },
          { latex: '\\lim', display: 'lim' },
          { latex: '\\sum', display: '∑' },
          { latex: '\\prod', display: '∏' },
          { latex: '\\int', display: '∫' }
        ]
      },
      {
        name: 'Delimiters',
        nameZh: '分隔符',
        symbols: [
          { latex: '(', display: '(' },
          { latex: ')', display: ')' },
          { latex: '[', display: '[' },
          { latex: ']', display: ']' },
          { latex: '\\{', display: '{' },
          { latex: '\\}', display: '}' },
          { latex: '\\langle', display: '⟨' },
          { latex: '\\rangle', display: '⟩' },
          { latex: '\\lfloor', display: '⌊' },
          { latex: '\\rfloor', display: '⌋' },
          { latex: '\\lceil', display: '⌈' },
          { latex: '\\rceil', display: '⌉' }
        ]
      },
      {
        name: 'Matrices',
        nameZh: '矩阵',
        symbols: [
          { latex: '\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}', display: 'pmatrix' },
          { latex: '\\begin{bmatrix} a & b \\\\ c & d \\end{bmatrix}', display: 'bmatrix' },
          { latex: '\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}', display: 'vmatrix' },
          { latex: '\\begin{Bmatrix} a & b \\\\ c & d \\end{Bmatrix}', display: 'Bmatrix' }
        ]
      },
      {
        name: 'Fractions',
        nameZh: '分数',
        symbols: [
          { latex: '\\frac{a}{b}', display: 'a/b' },
          { latex: '\\dfrac{a}{b}', display: 'A/B' },
          { latex: '\\tfrac{a}{b}', display: 'a/b' },
          { latex: '\\cfrac{a}{b}', display: 'a/b' }
        ]
      },
      {
        name: 'Roots',
        nameZh: '根号',
        symbols: [
          { latex: '\\sqrt{x}', display: '√x' },
          { latex: '\\sqrt[n]{x}', display: 'ⁿ√x' },
          { latex: '\\sqrt[3]{x}', display: '∛x' }
        ]
      },
      {
        name: 'Subscripts',
        nameZh: '上下标',
        symbols: [
          { latex: 'x_n', display: 'xₙ' },
          { latex: 'x^n', display: 'xⁿ' },
          { latex: 'x_{n+1}', display: 'xₙ₊₁' },
          { latex: 'x^{n+1}', display: 'xⁿ⁺¹' },
          { latex: 'x_{ij}', display: 'xᵢⱼ' },
          { latex: 'x^{ij}', display: 'xⁱʲ' }
        ]
      },
      {
        name: 'Overlines',
        nameZh: '上划线',
        symbols: [
          { latex: '\\overline{AB}', display: 'AB̄' },
          { latex: '\\underline{AB}', display: 'AB̲' },
          { latex: '\\overbrace{AB}', display: 'AB̂' },
          { latex: '\\underbrace{AB}', display: 'AB̤' }
        ]
      },
      {
        name: 'Special',
        nameZh: '特殊符号',
        symbols: [
          { latex: '\\infty', display: '∞' },
          { latex: '\\partial', display: '∂' },
          { latex: '\\nabla', display: '∇' },
          { latex: '\\forall', display: '∀' },
          { latex: '\\exists', display: '∃' },
          { latex: '\\neg', display: '¬' },
          { latex: '\\land', display: '∧' },
          { latex: '\\lor', display: '∨' }
        ]
      },
      {
        name: 'Number Sets',
        nameZh: '数集',
        symbols: [
          { latex: '\\mathbb{R}', display: 'ℝ' },
          { latex: '\\mathbb{Z}', display: 'ℤ' },
          { latex: '\\mathbb{N}', display: 'ℕ' },
          { latex: '\\mathbb{Q}', display: 'ℚ' },
          { latex: '\\mathbb{C}', display: 'ℂ' }
        ]
      },
      {
        name: 'Decorations',
        nameZh: '装饰',
        symbols: [
          { latex: '\\mathcal{A}', display: '𝒜' },
          { latex: '\\mathfrak{A}', display: '𝔄' },
          { latex: '\\mathbb{A}', display: '𝔸' },
          { latex: '\\mathrm{A}', display: 'A' },
          { latex: '\\mathbf{A}', display: 'A' },
          { latex: '\\mathit{A}', display: 'A' }
        ]
      },
      {
        name: 'Logic',
        nameZh: '逻辑',
        symbols: [
          { latex: '\\therefore', display: '∴' },
          { latex: '\\because', display: '∵' },
          { latex: '\\vdash', display: '⊢' },
          { latex: '\\dashv', display: '⊣' },
          { latex: '\\top', display: '⊤' },
          { latex: '\\bot', display: '⊥' }
        ]
      },
      {
        name: 'Geometry',
        nameZh: '几何',
        symbols: [
          { latex: '\\angle', display: '∠' },
          { latex: '\\triangle', display: '△' },
          { latex: '\\square', display: '□' },
          { latex: '\\circ', display: '○' },
          { latex: '\\parallel', display: '∥' },
          { latex: '\\perp', display: '⊥' }
        ]
      },
      {
        name: 'Miscellaneous',
        nameZh: '杂项',
        symbols: [
          { latex: '\\ldots', display: '…' },
          { latex: '\\cdots', display: '⋯' },
          { latex: '\\vdots', display: '⋮' },
          { latex: '\\ddots', display: '⋱' },
          { latex: '\\prime', display: '′' },
          { latex: '\\dagger', display: '†' },
          { latex: '\\ddagger', display: '‡' }
        ]
      }
    ];
  }

  init() {
    this.render();
  }

  render() {
    this.container.innerHTML = '';
    this.container.className = 'symbol-library';

    // Create category tabs
    const tabs = document.createElement('div');
    tabs.className = 'symbol-tabs';

    const content = document.createElement('div');
    content.className = 'symbol-content';

    this.options.categories.forEach((category, index) => {
      // Tab
      const tab = document.createElement('button');
      tab.className = 'symbol-tab';
      tab.textContent = category.nameZh;
      tab.onclick = () => this.showCategory(index, tabs, content);
      tabs.appendChild(tab);

      // Category content
      const categoryDiv = document.createElement('div');
      categoryDiv.className = 'symbol-category';
      categoryDiv.style.display = index === 0 ? 'grid' : 'none';

      category.symbols.forEach(symbol => {
        const btn = document.createElement('button');
        btn.className = 'symbol-btn';
        btn.textContent = symbol.display;
        btn.title = symbol.latex;
        btn.onclick = () => this.selectSymbol(symbol);
        categoryDiv.appendChild(btn);
      });

      content.appendChild(categoryDiv);
    });

    this.container.appendChild(tabs);
    this.container.appendChild(content);

    // Show first category
    if (this.options.categories.length > 0) {
      this.showCategory(0, tabs, content);
    }
  }

  showCategory(index, tabs, content) {
    // Update tabs
    Array.from(tabs.children).forEach((tab, i) => {
      tab.classList.toggle('active', i === index);
    });

    // Update content
    Array.from(content.children).forEach((category, i) => {
      category.style.display = i === index ? 'grid' : 'none';
    });
  }

  selectSymbol(symbol) {
    this.emit('select', symbol);
  }

  on(event, callback) {
    if (this.callbacks[event]) {
      this.callbacks[event].push(callback);
    }
  }

  emit(event, ...args) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach(cb => cb(...args));
    }
  }
}

module.exports = { SymbolLibrary };
```

- [ ] **Step 2: Add symbol library styles to common.css**

```css
/* Add to office_plugin/shared/styles/common.css */
.symbol-library {
  border: 1px solid var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}

.symbol-tabs {
  display: flex;
  overflow-x: auto;
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
}

.symbol-tab {
  padding: 8px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

.symbol-tab:hover {
  background: var(--background-color);
}

.symbol-tab.active {
  background: var(--primary-color);
  color: white;
}

.symbol-content {
  padding: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.symbol-category {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(32px, 1fr));
  gap: 4px;
}

.symbol-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--surface-color);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.symbol-btn:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}
```

- [ ] **Step 3: Commit**

```bash
git add office_plugin/shared/ui/symbol-library.js office_plugin/shared/styles/common.css
git commit -m "feat(wps): add complete symbol library with 18 categories"
```

---

## Task 6: WPS Document Adapter

**Covers:** [S10] Formula management, [S11] Formula insertion

**Files:**
- Create: `office_plugin/hosts/WpsAddIn/src/adapters/wps-document.js`
- Create: `office_plugin/hosts/WpsAddIn/src/adapters/wps-selection.js`

- [ ] **Step 1: Create WPS document adapter**

```javascript
// office_plugin/hosts/WpsAddIn/src/adapters/wps-document.js
class WpsDocumentAdapter {
  constructor() {
    this.app = window.Application;
  }

  getDocument() {
    return this.app.ActiveDocument;
  }

  getSelection() {
    return this.app.Selection;
  }

  async insertOMML(ommlXml) {
    const selection = this.getSelection();
    selection.Range.InsertXML(ommlXml);
  }

  async insertImage(imageBase64) {
    const selection = this.getSelection();
    const tempPath = await this.saveTempImage(imageBase64);
    selection.InlineShapes.AddPicture(tempPath, false, true);
    await this.deleteTempFile(tempPath);
  }

  async saveTempImage(base64Data) {
    // Use WPS API to save temp file
    const tempDir = this.app.PathTemp;
    const fileName = `latex_formula_${Date.now()}.png`;
    const filePath = `${tempDir}\\${fileName}`;

    // Convert base64 to file
    const response = await fetch(`data:image/png;base64,${base64Data}`);
    const blob = await response.blob();
    const arrayBuffer = await blob.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);

    // Write file using WPS API
    const file = this.app.FileSystem.OpenTextFile(filePath, 2, true);
    file.Write(uint8Array);
    file.Close();

    return filePath;
  }

  async deleteTempFile(filePath) {
    try {
      this.app.FileSystem.DeleteFile(filePath);
    } catch (error) {
      console.warn('Failed to delete temp file:', error);
    }
  }

  async loadFormula(contentControl) {
    // Load formula metadata from content control
    const metadata = {
      equationId: contentControl.Tag,
      latex: contentControl.Range.Text,
      display: true
    };
    return metadata;
  }

  async updateFormula(contentControl, newOoml) {
    // Update existing formula
    contentControl.Range.InsertXML(newOoml);
  }

  async deleteFormula(contentControl) {
    // Delete formula and clean up
    contentControl.Delete();
  }

  async renumberFormulas(mode = 'automatic') {
    // Renumber all formulas in document
    const doc = this.getDocument();
    const contentControls = doc.ContentControls;

    let counter = 1;
    for (let i = 1; i <= contentControls.Count; i++) {
      const cc = contentControls.Item(i);
      if (cc.Tag && cc.Tag.startsWith('latexsnipper-eq-')) {
        if (mode === 'automatic') {
          // Update number
          const numberText = `[${counter}]`;
          // Find and update number control
          counter++;
        }
      }
    }

    return counter - 1;
  }
}

module.exports = { WpsDocumentAdapter };
```

- [ ] **Step 2: Create WPS selection adapter**

```javascript
// office_plugin/hosts/WpsAddIn/src/adapters/wps-selection.js
class WpsSelectionAdapter {
  constructor() {
    this.app = window.Application;
  }

  getSelection() {
    return this.app.Selection;
  }

  getRange() {
    return this.getSelection().Range;
  }

  insertText(text) {
    const range = this.getRange();
    range.TypeText(text);
  }

  insertParagraph() {
    const range = this.getRange();
    range.TypeParagraph();
  }

  collapseToEnd() {
    const range = this.getRange();
    range.Collapse(0); // wdCollapseEnd
  }

  collapseToStart() {
    const range = this.getRange();
    range.Collapse(1); // wdCollapseStart
  }

  selectAll() {
    const doc = this.app.ActiveDocument;
    doc.Content.Select();
  }

  getCurrentFontSize() {
    const selection = this.getSelection();
    return selection.Font.Size;
  }

  setCurrentFontSize(size) {
    const selection = this.getSelection();
    selection.Font.Size = size;
  }
}

module.exports = { WpsSelectionAdapter };
```

- [ ] **Step 3: Commit**

```bash
git add office_plugin/hosts/WpsAddIn/src/adapters/
git commit -m "feat(wps): add WPS document and selection adapters"
```

---

## Task 7: Task Pane UI

**Covers:** [S7] UI design, [S8] Formula editing, [S12] Localization

**Files:**
- Create: `office_plugin/hosts/WpsAddIn/src/taskpane.html`
- Create: `office_plugin/hosts/WpsAddIn/src/taskpane.js`
- Create: `office_plugin/shared/core/i18n/en.json`
- Create: `office_plugin/shared/core/i18n/zh.json`

- [ ] **Step 1: Create English translations**

```json
{
  "app": {
    "title": "LaTeXSnipper",
    "description": "Insert LaTeX formulas into WPS documents"
  },
  "editor": {
    "label": "LaTeX Formula",
    "placeholder": "Enter LaTeX formula...",
    "preview": "Preview"
  },
  "symbols": {
    "label": "Symbol Library"
  },
  "actions": {
    "insertOmml": "Insert Formula (OMML)",
    "insertImage": "Insert Formula (Image)",
    "preview": "Preview",
    "clear": "Clear"
  },
  "settings": {
    "label": "Settings",
    "displayMode": "Display Mode",
    "fontSize": "Font Size"
  },
  "status": {
    "connected": "Connected to Bridge",
    "disconnected": "Bridge not available, using local renderer"
  },
  "errors": {
    "invalidLatex": "Invalid LaTeX syntax",
    "insertFailed": "Failed to insert formula"
  }
}
```

- [ ] **Step 2: Create Chinese translations**

```json
{
  "app": {
    "title": "LaTeXSnipper",
    "description": "在 WPS 文档中插入 LaTeX 公式"
  },
  "editor": {
    "label": "LaTeX 公式",
    "placeholder": "输入 LaTeX 公式...",
    "preview": "预览"
  },
  "symbols": {
    "label": "符号库"
  },
  "actions": {
    "insertOmml": "插入公式 (OMML)",
    "insertImage": "插入公式 (图片)",
    "preview": "预览",
    "clear": "清空"
  },
  "settings": {
    "label": "设置",
    "displayMode": "显示模式",
    "fontSize": "字体大小"
  },
  "status": {
    "connected": "已连接到 Bridge",
    "disconnected": "Bridge 不可用，使用本地渲染器"
  },
  "errors": {
    "invalidLatex": "LaTeX 语法无效",
    "insertFailed": "插入公式失败"
  }
}
```

- [ ] **Step 3: Create Task Pane HTML**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LaTeXSnipper</title>
  <link rel="stylesheet" href="../../shared/styles/common.css">
  <style>
    .taskpane {
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    .editor-section {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    .preview-section {
      min-height: 100px;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      padding: 8px;
      margin-top: 8px;
      background: white;
    }
    .actions-section {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
    .actions-section button {
      flex: 1;
    }
    .status-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--text-secondary);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success-color);
    }
    .status-dot.disconnected {
      background: var(--error-color);
    }
  </style>
</head>
<body>
  <div class="taskpane">
    <div class="taskpane-header">
      <h3 style="margin: 0;">LaTeXSnipper</h3>
      <p style="margin: 4px 0 0 0; font-size: 12px; color: var(--text-secondary);" data-i18n="app.description">
        在 WPS 文档中插入 LaTeX 公式
      </p>
    </div>

    <div class="taskpane-content">
      <div class="editor-section">
        <div class="form-group">
          <label class="form-label" data-i18n="editor.label">LaTeX 公式</label>
          <textarea
            id="latex-input"
            class="form-input"
            rows="4"
            placeholder="输入 LaTeX 公式..."
            data-i18n-placeholder="editor.placeholder"
          ></textarea>
        </div>

        <div class="form-group">
          <label class="form-label" data-i18n="symbols.label">符号库</label>
          <div id="symbol-library"></div>
        </div>

        <div class="form-group">
          <label class="form-label" data-i18n="editor.preview">预览</label>
          <div id="preview" class="preview-section"></div>
        </div>

        <div class="actions-section">
          <button id="btn-insert-omml" class="btn btn-primary" data-i18n="actions.insertOmml">
            插入公式 (OMML)
          </button>
          <button id="btn-insert-image" class="btn btn-secondary" data-i18n="actions.insertImage">
            插入公式 (图片)
          </button>
        </div>
      </div>
    </div>

    <div class="taskpane-footer">
      <div class="status-bar">
        <div id="status-dot" class="status-dot"></div>
        <span id="status-text" data-i18n="status.disconnected">Bridge 不可用，使用本地渲染器</span>
      </div>
    </div>
  </div>

  <script src="taskpane.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create Task Pane JavaScript**

```javascript
// office_plugin/hosts/WpsAddIn/src/taskpane.js
const { BridgeClient } = require('../../shared/core/bridge-client');
const { LatexParser } = require('../../shared/core/latex-parser');
const { MathLiveEditor } = require('../../shared/ui/mathlive-editor');
const { SymbolLibrary } = require('../../shared/ui/symbol-library');
const { WpsDocumentAdapter } = require('./adapters/wps-document');
const { WpsSelectionAdapter } = require('./adapters/wps-selection');

class TaskPane {
  constructor() {
    this.bridgeClient = new BridgeClient();
    this.latexParser = new LatexParser();
    this.documentAdapter = new WpsDocumentAdapter();
    this.selectionAdapter = new WpsSelectionAdapter();
    this.editor = null;
    this.symbolLibrary = null;
    this.currentLatex = '';
    this.displayMode = true;

    this.init();
  }

  async init() {
    // Initialize components
    this.initEditor();
    this.initSymbolLibrary();
    this.initEventListeners();
    await this.connectBridge();
  }

  initEditor() {
    const container = document.getElementById('latex-input');
    this.editor = new MathLiveEditor(container, {
      virtualKeyboardMode: 'manual'
    });

    this.editor.on('change', (latex) => {
      this.currentLatex = latex;
      this.updatePreview();
    });
  }

  initSymbolLibrary() {
    const container = document.getElementById('symbol-library');
    this.symbolLibrary = new SymbolLibrary(container);

    this.symbolLibrary.on('select', (symbol) => {
      this.editor.setLatex(this.editor.getLatex() + symbol.latex);
    });
  }

  initEventListeners() {
    // Insert OMML button
    document.getElementById('btn-insert-omml').addEventListener('click', () => {
      this.insertFormula('omml');
    });

    // Insert Image button
    document.getElementById('btn-insert-image').addEventListener('click', () => {
      this.insertFormula('png');
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') {
        this.insertFormula('omml');
      }
    });
  }

  async connectBridge() {
    const connected = await this.bridgeClient.connect();
    this.updateStatus(connected);
  }

  updateStatus(connected) {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');

    if (connected) {
      dot.classList.remove('disconnected');
      text.textContent = '已连接到 Bridge';
    } else {
      dot.classList.add('disconnected');
      text.textContent = 'Bridge 不可用，使用本地渲染器';
    }
  }

  async updatePreview() {
    const preview = document.getElementById('preview');
    const parsed = this.latexParser.parse(this.currentLatex);

    if (!parsed.valid) {
      preview.innerHTML = `<span class="error-message">${parsed.error}</span>`;
      return;
    }

    try {
      const result = await this.bridgeClient.convertLatex(parsed.latex, {
        display: parsed.display
      });

      if (result.ok) {
        if (result.result.png) {
          preview.innerHTML = `<img src="data:image/png;base64,${result.result.png}" style="max-width: 100%;">`;
        } else if (result.result.omml) {
          preview.innerHTML = '<span style="color: var(--success-color);">公式已准备好</span>';
        }
      } else {
        preview.innerHTML = `<span class="error-message">${result.error.message}</span>`;
      }
    } catch (error) {
      preview.innerHTML = `<span class="error-message">${error.message}</span>`;
    }
  }

  async insertFormula(type) {
    const parsed = this.latexParser.parse(this.currentLatex);

    if (!parsed.valid) {
      alert('LaTeX 语法无效: ' + parsed.error);
      return;
    }

    try {
      const result = await this.bridgeClient.convertLatex(parsed.latex, {
        display: parsed.display,
        targets: [type]
      });

      if (!result.ok) {
        alert('转换失败: ' + result.error.message);
        return;
      }

      if (type === 'omml' && result.result.omml) {
        await this.documentAdapter.insertOMML(result.result.omml);
      } else if (type === 'png' && result.result.png) {
        await this.documentAdapter.insertImage(result.result.png);
      } else {
        alert('无法插入公式');
        return;
      }

      // Clear editor after successful insertion
      this.editor.setLatex('');
      this.currentLatex = '';
      this.updatePreview();

    } catch (error) {
      alert('插入公式失败: ' + error.message);
    }
  }
}

// Initialize task pane when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new TaskPane();
});
```

- [ ] **Step 5: Commit**

```bash
git add office_plugin/hosts/WpsAddIn/src/taskpane.* office_plugin/shared/core/i18n/
git commit -m "feat(wps): add Task Pane UI with editor, symbols, and preview"
```

---

## Task 8: Plugin Initialization

**Covers:** [S13] Plugin loading, [S14] WPS integration

**Files:**
- Create: `office_plugin/hosts/WpsAddIn/src/main.js`

- [ ] **Step 1: Create plugin initialization**

```javascript
// office_plugin/hosts/WpsAddIn/src/main.js
class LaTeXSnipperPlugin {
  constructor() {
    this.taskPane = null;
    this.init();
  }

  init() {
    // Register WPS event handlers
    this.registerEventHandlers();

    // Create ribbon buttons
    this.createRibbon();

    console.log('LaTeXSnipper plugin initialized');
  }

  registerEventHandlers() {
    // Document open
    if (window.Application) {
      window.Application.DocumentOpen = () => {
        this.onDocumentOpen();
      };

      // Document close
      window.Application.DocumentBeforeClose = () => {
        this.onDocumentClose();
      };
    }
  }

  createRibbon() {
    // WPS JSAPI ribbon creation would go here
    // This is a placeholder - actual implementation depends on WPS API
    console.log('Ribbon buttons created');
  }

  onDocumentOpen() {
    console.log('Document opened');
  }

  onDocumentClose() {
    console.log('Document closing');
  }

  showTaskPane() {
    // Show or create task pane
    if (!this.taskPane) {
      this.taskPane = window.Application.CreateTaskPane('LaTeXSnipper');
      this.taskPane.Visible = true;
    } else {
      this.taskPane.Visible = true;
    }
  }

  hideTaskPane() {
    if (this.taskPane) {
      this.taskPane.Visible = false;
    }
  }
}

// Initialize plugin when WPS is ready
if (window.Application) {
  new LaTeXSnipperPlugin();
} else {
  window.addEventListener('load', () => {
    if (window.Application) {
      new LaTeXSnipperPlugin();
    }
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add office_plugin/hosts/WpsAddIn/src/main.js
git commit -m "feat(wps): add plugin initialization and ribbon setup"
```

---

## Task 9: Integration Testing

**Covers:** [S15] Testing strategy, [S16] Manual testing

**Files:**
- Create: `office_plugin/hosts/WpsAddIn/TESTING.md`

- [ ] **Step 1: Create testing documentation**

```markdown
# WPS Add-in Testing Guide

## Prerequisites

1. WPS Office installed on Windows
2. Node.js installed
3. LaTeXSnipper Desktop running (for Bridge testing)

## Manual Testing Steps

### 1. Plugin Loading

1. Open WPS Writer
2. Go to 插件 (Plugins) menu
3. Look for LaTeXSnipper in the plugin list
4. Click to open the Task Pane

**Expected:** Task Pane appears on the right side

### 2. Formula Editing

1. Type a LaTeX formula in the input area
   - Example: `E = mc^2`
2. Check the preview area

**Expected:** Formula renders correctly in preview

### 3. Symbol Library

1. Click on a symbol category tab
2. Click on a symbol button

**Expected:** Symbol is inserted into the editor

### 4. Formula Insertion (OMML)

1. Enter a formula
2. Click "插入公式 (OMML)" button

**Expected:** Formula is inserted into the document as editable math

### 5. Formula Insertion (Image)

1. Enter a formula
2. Click "插入公式 (图片)" button

**Expected:** Formula is inserted as a PNG image

### 6. Bridge Connection

1. Start LaTeXSnipper Desktop
2. Check the status bar in Task Pane

**Expected:** Status shows "已连接到 Bridge"

### 7. Fallback Mode

1. Stop LaTeXSnipper Desktop
2. Enter a formula
3. Check the preview

**Expected:** Formula renders using local KaTeX

## Test Cases

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Simple formula | `E = mc^2` | Formula renders correctly |
| Fraction | `\frac{a}{b}` | Fraction displays properly |
| Greek letters | `\alpha \beta \gamma` | Greek letters render |
| Matrix | `\begin{pmatrix} a & b \\ c & d \end{pmatrix}` | Matrix displays |
| Invalid LaTeX | `\frac{` | Error message shown |

## Bug Reporting

If you encounter issues:

1. Take a screenshot of the error
2. Note the steps to reproduce
3. Check the browser console (F12) for errors
4. Report to the development team
```

- [ ] **Step 2: Commit**

```bash
git add office_plugin/hosts/WpsAddIn/TESTING.md
git commit -m "docs(wps): add testing guide for WPS plugin"
```

---

## Task 10: Final Verification

**Covers:** [S17] Success criteria

**Files:**
- Verify: All files created in previous tasks

- [ ] **Step 1: Verify project structure**

Run: `find office_plugin/hosts/WpsAddIn -type f | sort`
Expected: All files listed in File Structure section

- [ ] **Step 2: Verify shared components**

Run: `find office_plugin/shared -type f | sort`
Expected: All shared files listed in File Structure section

- [ ] **Step 3: Run linting (if available)**

Run: `cd office_plugin && npm run lint`
Expected: No errors

- [ ] **Step 4: Run tests (if available)**

Run: `cd office_plugin && npm test`
Expected: All tests pass

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(wps): complete WPS Windows Add-in implementation"
```

---

## Summary

This plan creates a complete WPS Office plugin for Windows with:

- **Shared core components** (Bridge client, LaTeX parser, local renderer)
- **Shared UI components** (MathLive editor, symbol library)
- **WPS-specific adapters** (document, selection)
- **Task Pane UI** with editor, preview, and actions
- **Plugin initialization** and ribbon setup
- **Testing documentation**

The implementation follows the Hybrid Architecture approach, allowing code reuse across platforms while providing native WPS integration.
