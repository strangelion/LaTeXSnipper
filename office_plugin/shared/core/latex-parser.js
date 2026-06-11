class LatexParser {
  parse(input) {
    if (!input || typeof input !== 'string') {
      return { valid: false, error: 'Invalid input', latex: '', display: false };
    }

    const trimmed = input.trim();

    let display = false;
    let latex = trimmed;

    if (trimmed.startsWith('\\[') && trimmed.endsWith('\\]')) {
      display = true;
      latex = trimmed.slice(2, -2).trim();
    } else if (trimmed.startsWith('\\begin{equation}') && trimmed.endsWith('\\end{equation}')) {
      display = true;
      latex = trimmed.slice(16, -15).trim();
    } else if (trimmed.startsWith('$$') && trimmed.endsWith('$$')) {
      display = true;
      latex = trimmed.slice(2, -2).trim();
    } else if (trimmed.startsWith('$') && trimmed.endsWith('$')) {
      display = false;
      latex = trimmed.slice(1, -1).trim();
    }

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

    latex = this.normalizeLatex(latex);

    return {
      valid: true,
      latex,
      display,
      error: null
    };
  }

  normalizeLatex(latex) {
    return latex.replace(/\^(\d+)/g, '^{$1}')
                .replace(/_(\d+)/g, '_{$1}');
  }
}

module.exports = { LatexParser };
