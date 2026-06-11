// office_plugin/hosts/WpsAddIn/src/taskpane.js
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
    this.initEditor();
    this.initSymbolLibrary();
    this.initEventListeners();
    await this.connectBridge();
    await this.initI18n();
  }

  async initI18n() {
    const lang = navigator.language.startsWith('zh') ? 'zh' : 'en';

    try {
      const response = await fetch(`../../shared/core/i18n/${lang}.json`);
      const translations = await response.json();

      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const keys = key.split('.');
        let value = translations;
        for (const k of keys) {
          value = value?.[k];
        }
        if (value) {
          el.textContent = value;
        }
      });

      document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        const keys = key.split('.');
        let value = translations;
        for (const k of keys) {
          value = value?.[k];
        }
        if (value) {
          el.placeholder = value;
        }
      });
    } catch (error) {
      console.warn('Failed to load translations:', error);
    }
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
    document.getElementById('btn-insert-omml').addEventListener('click', () => {
      this.insertFormula('omml');
    });

    document.getElementById('btn-insert-image').addEventListener('click', () => {
      this.insertFormula('png');
    });

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
      preview.innerHTML = '<span class="error-message">' + parsed.error + '</span>';
      return;
    }

    try {
      const result = await this.bridgeClient.convertLatex(parsed.latex, {
        display: parsed.display
      });

      if (result.ok) {
        if (result.result.png) {
          preview.innerHTML = '<img src="data:image/png;base64,' + result.result.png + '" style="max-width: 100%;">';
        } else if (result.result.omml) {
          preview.innerHTML = '<span style="color: var(--success-color);">公式已准备好</span>';
        }
      } else {
        preview.innerHTML = '<span class="error-message">' + result.error.message + '</span>';
      }
    } catch (error) {
      preview.innerHTML = '<span class="error-message">' + error.message + '</span>';
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

      this.editor.setLatex('');
      this.currentLatex = '';
      this.updatePreview();

    } catch (error) {
      alert('插入公式失败: ' + error.message);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new TaskPane();
});
