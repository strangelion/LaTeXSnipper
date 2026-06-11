const { BridgeClient } = require('../bridge-client');
const { LocalRenderer } = require('../local-renderer');

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

  test('should fallback to local renderer when bridge unavailable', async () => {
    const client = new BridgeClient('http://invalid:99999');
    const connected = await client.connect();
    expect(connected).toBe(false);
    expect(client.isConnected).toBe(false);
    expect(client.localRenderer).toBeInstanceOf(LocalRenderer);
  });

  test('should convert latex using local renderer when not connected', async () => {
    const client = new BridgeClient('http://invalid:99999');
    await client.connect();
    const result = await client.convertLatex('E = mc^2');
    expect(result.ok).toBe(true);
    expect(result.result.latex).toBe('E = mc^2');
  });

  test('should reject null input', async () => {
    const client = new BridgeClient();
    const result = await client.convertLatex(null);
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('invalid_input');
  });

  test('should reject undefined input', async () => {
    const client = new BridgeClient();
    const result = await client.convertLatex(undefined);
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('invalid_input');
  });

  test('should reject empty string input', async () => {
    const client = new BridgeClient();
    const result = await client.convertLatex('');
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('invalid_input');
  });

  test('should reject non-string input', async () => {
    const client = new BridgeClient();
    const result = await client.convertLatex(123);
    expect(result.ok).toBe(false);
    expect(result.error.code).toBe('invalid_input');
  });
});

describe('LocalRenderer', () => {
  test('should convert valid latex', async () => {
    const renderer = new LocalRenderer();
    const result = await renderer.convert('E = mc^2');
    expect(result.ok).toBe(true);
    expect(result.result.latex).toBe('E = mc^2');
    expect(result.result.display).toBe(true);
  });

  test('should handle display mode option', async () => {
    const renderer = new LocalRenderer();
    const result = await renderer.convert('E = mc^2', { display: false });
    expect(result.ok).toBe(true);
    expect(result.result.display).toBe(false);
  });
});
