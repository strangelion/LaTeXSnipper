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
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdn.jsdelivr.net/npm/mathlive@0.95.5/dist/mathlive-static.css';
    document.head.appendChild(link);

    const mathfield = document.createElement('div');
    mathfield.className = 'mathfield';
    mathfield.setAttribute('virtual-keyboard-mode', this.options.virtualKeyboardMode);
    this.container.appendChild(mathfield);

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
