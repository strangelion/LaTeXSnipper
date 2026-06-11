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
          { latex: '\\alpha', display: '\u03B1' },
          { latex: '\\beta', display: '\u03B2' },
          { latex: '\\gamma', display: '\u03B3' },
          { latex: '\\delta', display: '\u03B4' },
          { latex: '\\epsilon', display: '\u03B5' },
          { latex: '\\zeta', display: '\u03B6' },
          { latex: '\\eta', display: '\u03B7' },
          { latex: '\\theta', display: '\u03B8' },
          { latex: '\\iota', display: '\u03B9' },
          { latex: '\\kappa', display: '\u03BA' },
          { latex: '\\lambda', display: '\u03BB' },
          { latex: '\\mu', display: '\u03BC' },
          { latex: '\\nu', display: '\u03BD' },
          { latex: '\\xi', display: '\u03BE' },
          { latex: '\\pi', display: '\u03C0' },
          { latex: '\\rho', display: '\u03C1' },
          { latex: '\\sigma', display: '\u03C3' },
          { latex: '\\tau', display: '\u03C4' },
          { latex: '\\upsilon', display: '\u03C5' },
          { latex: '\\phi', display: '\u03C6' },
          { latex: '\\chi', display: '\u03C7' },
          { latex: '\\psi', display: '\u03C8' },
          { latex: '\\omega', display: '\u03C9' }
        ]
      },
      {
        name: 'Operators',
        nameZh: '运算符',
        symbols: [
          { latex: '+', display: '+' },
          { latex: '-', display: '\u2212' },
          { latex: '\\times', display: '\u00D7' },
          { latex: '\\div', display: '\u00F7' },
          { latex: '\\pm', display: '\u00B1' },
          { latex: '\\mp', display: '\u2213' },
          { latex: '\\cdot', display: '\u00B7' },
          { latex: '\\ast', display: '\u2217' },
          { latex: '\\circ', display: '\u2218' },
          { latex: '\\bullet', display: '\u2022' }
        ]
      },
      {
        name: 'Relations',
        nameZh: '关系符',
        symbols: [
          { latex: '=', display: '=' },
          { latex: '\\neq', display: '\u2260' },
          { latex: '<', display: '<' },
          { latex: '>', display: '>' },
          { latex: '\\leq', display: '\u2264' },
          { latex: '\\geq', display: '\u2265' },
          { latex: '\\approx', display: '\u2248' },
          { latex: '\\equiv', display: '\u2261' },
          { latex: '\\sim', display: '\u223C' },
          { latex: '\\simeq', display: '\u2243' }
        ]
      },
      {
        name: 'Arrows',
        nameZh: '箭头',
        symbols: [
          { latex: '\\leftarrow', display: '\u2190' },
          { latex: '\\rightarrow', display: '\u2192' },
          { latex: '\\leftrightarrow', display: '\u2194' },
          { latex: '\\Leftarrow', display: '\u21D0' },
          { latex: '\\Rightarrow', display: '\u21D2' },
          { latex: '\\Leftrightarrow', display: '\u21D4' },
          { latex: '\\uparrow', display: '\u2191' },
          { latex: '\\downarrow', display: '\u2193' }
        ]
      },
      {
        name: 'Accents',
        nameZh: '重音',
        symbols: [
          { latex: '\\hat{a}', display: '\u00E2' },
          { latex: '\\bar{a}', display: '\u0101' },
          { latex: '\\dot{a}', display: '\u0227' },
          { latex: '\\ddot{a}', display: '\u00E4' },
          { latex: '\\tilde{a}', display: '\u00E3' },
          { latex: '\\vec{a}', display: 'a\u20D7' }
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
          { latex: '\\sum', display: '\u2211' },
          { latex: '\\prod', display: '\u220F' },
          { latex: '\\int', display: '\u222B' }
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
          { latex: '\\langle', display: '\u27E8' },
          { latex: '\\rangle', display: '\u27E9' },
          { latex: '\\lfloor', display: '\u230A' },
          { latex: '\\rfloor', display: '\u230B' },
          { latex: '\\lceil', display: '\u2308' },
          { latex: '\\rceil', display: '\u2309' }
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
          { latex: '\\sqrt{x}', display: '\u221Ax' },
          { latex: '\\sqrt[n]{x}', display: '\u207F\u221Ax' },
          { latex: '\\sqrt[3]{x}', display: '\u221Bx' }
        ]
      },
      {
        name: 'Subscripts',
        nameZh: '上下标',
        symbols: [
          { latex: 'x_n', display: 'x\u2099' },
          { latex: 'x^n', display: 'x\u207F' },
          { latex: 'x_{n+1}', display: 'x\u2099\u207A\u2081' },
          { latex: 'x^{n+1}', display: 'x\u207F\u207A\u00B9' },
          { latex: 'x_{ij}', display: 'x\u1D62\u2C7C' },
          { latex: 'x^{ij}', display: 'x\u1D62\u02B9' }
        ]
      },
      {
        name: 'Overlines',
        nameZh: '上划线',
        symbols: [
          { latex: '\\overline{AB}', display: 'AB\u0304' },
          { latex: '\\underline{AB}', display: 'AB\u0332' },
          { latex: '\\overbrace{AB}', display: 'AB\u0302' },
          { latex: '\\underbrace{AB}', display: 'AB\u0324' }
        ]
      },
      {
        name: 'Special',
        nameZh: '特殊符号',
        symbols: [
          { latex: '\\infty', display: '\u221E' },
          { latex: '\\partial', display: '\u2202' },
          { latex: '\\nabla', display: '\u2207' },
          { latex: '\\forall', display: '\u2200' },
          { latex: '\\exists', display: '\u2203' },
          { latex: '\\neg', display: '\u00AC' },
          { latex: '\\land', display: '\u2227' },
          { latex: '\\lor', display: '\u2228' }
        ]
      },
      {
        name: 'Number Sets',
        nameZh: '数集',
        symbols: [
          { latex: '\\mathbb{R}', display: '\u211D' },
          { latex: '\\mathbb{Z}', display: '\u2124' },
          { latex: '\\mathbb{N}', display: '\u2115' },
          { latex: '\\mathbb{Q}', display: '\u211A' },
          { latex: '\\mathbb{C}', display: '\u2102' }
        ]
      },
      {
        name: 'Decorations',
        nameZh: '装饰',
        symbols: [
          { latex: '\\mathcal{A}', display: '\uD835\uDC9C' },
          { latex: '\\mathfrak{A}', display: '\uD835\uDD04' },
          { latex: '\\mathbb{A}', display: '\u2110' },
          { latex: '\\mathrm{A}', display: 'A' },
          { latex: '\\mathbf{A}', display: 'A' },
          { latex: '\\mathit{A}', display: 'A' }
        ]
      },
      {
        name: 'Logic',
        nameZh: '逻辑',
        symbols: [
          { latex: '\\therefore', display: '\u2234' },
          { latex: '\\because', display: '\u2235' },
          { latex: '\\vdash', display: '\u22A2' },
          { latex: '\\dashv', display: '\u22A3' },
          { latex: '\\top', display: '\u22A4' },
          { latex: '\\bot', display: '\u22A5' }
        ]
      },
      {
        name: 'Geometry',
        nameZh: '几何',
        symbols: [
          { latex: '\\angle', display: '\u2220' },
          { latex: '\\triangle', display: '\u25B3' },
          { latex: '\\square', display: '\u25A1' },
          { latex: '\\circ', display: '\u25CB' },
          { latex: '\\parallel', display: '\u2225' },
          { latex: '\\perp', display: '\u22A5' }
        ]
      },
      {
        name: 'Miscellaneous',
        nameZh: '杂项',
        symbols: [
          { latex: '\\ldots', display: '\u2026' },
          { latex: '\\cdots', display: '\u22EF' },
          { latex: '\\vdots', display: '\u22EE' },
          { latex: '\\ddots', display: '\u22F1' },
          { latex: '\\prime', display: '\u2032' },
          { latex: '\\dagger', display: '\u2020' },
          { latex: '\\ddagger', display: '\u2021' }
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

    const tabs = document.createElement('div');
    tabs.className = 'symbol-tabs';

    const content = document.createElement('div');
    content.className = 'symbol-content';

    this.options.categories.forEach((category, index) => {
      const tab = document.createElement('button');
      tab.className = 'symbol-tab';
      tab.textContent = category.nameZh;
      tab.onclick = () => this.showCategory(index, tabs, content);
      tabs.appendChild(tab);

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

    if (this.options.categories.length > 0) {
      this.showCategory(0, tabs, content);
    }
  }

  showCategory(index, tabs, content) {
    Array.from(tabs.children).forEach((tab, i) => {
      tab.classList.toggle('active', i === index);
    });

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
