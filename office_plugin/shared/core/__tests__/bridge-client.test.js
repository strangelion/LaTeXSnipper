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