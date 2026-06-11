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
