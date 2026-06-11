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
|-----------|-------|------------------|
| Simple formula | `E = mc^2` | Formula renders correctly |
| Fraction | `\frac{a}{b}` | Fraction displays properly |
| Greek letters | `\alpha \beta \gamma` | Greek letters render |
| Matrix | `\begin{pmatrix} a & b \\\\ c & d \end{pmatrix}` | Matrix displays |
| Invalid LaTeX | `\frac{` | Error message shown |

## Bug Reporting

If you encounter issues:

1. Take a screenshot of the error
2. Note the steps to reproduce
3. Check the browser console (F12) for errors
4. Report to the development team