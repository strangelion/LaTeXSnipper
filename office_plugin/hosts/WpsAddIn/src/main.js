// office_plugin/hosts/WpsAddIn/src/main.js
class LaTeXSnipperPlugin {
  constructor() {
    this.init();
  }

  init() {
    this.registerEventHandlers();
    this.createRibbon();
    console.log('LaTeXSnipper plugin initialized');
  }

  registerEventHandlers() {
    if (window.Application) {
      window.Application.DocumentOpen = () => {
        this.onDocumentOpen();
      };

      window.Application.DocumentBeforeClose = () => {
        this.onDocumentClose();
      };
    }
  }

  createRibbon() {
    console.log('Ribbon buttons created');
  }

  onDocumentOpen() {
    console.log('Document opened');
  }

  onDocumentClose() {
    console.log('Document closing');
  }

  showTaskPane() {
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
