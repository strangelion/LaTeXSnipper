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