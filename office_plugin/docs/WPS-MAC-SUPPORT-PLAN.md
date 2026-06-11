# LaTeXSnipper Office Plugin: WPS & Mac Support Plan

## Overview

This document outlines the architecture and implementation plan for adding WPS Office and macOS support to the LaTeXSnipper Office Plugin.

## Current State

- **Supported**: Microsoft Office (Word/PowerPoint) on Windows via VSTO
- **Architecture**: C# VSTO Add-in + HTTP Bridge (127.0.0.1:28765)
- **Features**: OLE formulas, OMML insertion, PNG rendering, formula management

## Target Support

| Platform | Microsoft Office | WPS Office |
|----------|------------------|------------|
| Windows | ✅ Current (VSTO) | 🆕 WPS Add-in (JSAPI) |
| macOS | 🆕 Office Web Add-in | 🆕 WPS Add-in (JSAPI) |

---

## User Requirements (Brainstorm Session)

### Priority
- **First**: WPS Windows Add-in

### UI Design
- **Approach**: Reuse existing MathLive editor (consistent with Word plugin)

### Formula Insertion
- **Support**: Both OMML and PNG (user choice)

### Bridge Integration
- **Mode**: Hybrid (prefer Bridge, fallback to local KaTeX renderer)

### Symbol Library
- **Scope**: Complete library (all 18 categories)

### Formula Management
- **Features**: Full management (load, update, delete, renumber)

### Numbering
- **Support**: Automatic + Manual numbering

### Localization
- **Languages**: Chinese and English bilingual

### Screenshot OCR
- **Support**: Yes (via Bridge)

### Implementation Approach
- **Architecture**: Hybrid (shared core + platform-specific adapters)

---

## Architecture Design

### 1. WPS Windows Add-in (JSAPI)

**Technology**: WPS JS API (JavaScript/HTML/CSS)
**Architecture**: Task Pane + HTTP Bridge

```
WPS Desktop App (Windows)
  └── Chromium WebView
       ├── Task Pane UI (HTML/CSS/JS)
       │    ├── MathLive Formula Editor
       │    ├── LaTeX Input
       │    ├── Symbol Library
       │    └── Preview
       └── WPS JS API Bridge
            ├── Document Operations
            └── Selection Management
                    ↓
            HTTP Bridge (127.0.0.1:28765)
                    ↓
            LaTeXSnipper Desktop
```

**Key Differences from VSTO**:
- UI: HTML/CSS/JS instead of WinForms/WPF
- API: WPS JS API instead of COM automation
- Formula Insertion: OMML XML or PNG image
- No OLE support (use image fallback)

### 2. Microsoft Office macOS Add-in (Web Add-in)

**Technology**: Office.js + Task Pane
**Architecture**: Similar to WPS but using Office.js API

```
Microsoft Office Mac App
  └── WKWebView (Safari)
       ├── Task Pane UI (HTML/CSS/JS)
       │    ├── MathLive Formula Editor
       │    ├── LaTeX Input
       │    └── Preview
       └── Office.js API
            ├── Word.run() API
            └── Selection Management
                    ↓
            HTTP Bridge (127.0.0.1:28765)
                    ↓
            LaTeXSnipper Desktop
```

**Key Differences from Windows VSTO**:
- No COM/VSTO support on macOS
- Uses Office.js API (similar to Web Add-ins)
- WKWebView instead of WebView2
- Limited desktop-specific APIs

### 3. WPS macOS Add-in (JSAPI)

**Technology**: WPS JS API (same as Windows)
**Architecture**: Task Pane + HTTP Bridge

```
WPS Office Mac App
  └── Chromium WebView
       ├── Task Pane UI (HTML/CSS/JS)
       └── WPS JS API Bridge
                    ↓
            HTTP Bridge (127.0.0.1:28765)
                    ↓
            LaTeXSnipper Desktop
```

**Note**: WPS macOS uses Chromium WebView (not Safari), which simplifies cross-platform development.

---

## Project Structure

```
office_plugin/
├── src/                          # Shared libraries (existing)
│   ├── LaTeXSnipper.OfficePlugin.Abstractions/
│   ├── LaTeXSnipper.OfficePlugin.Bridge/
│   ├── LaTeXSnipper.OfficePlugin.Editor/
│   └── LaTeXSnipper.OfficePlugin.Rendering/
│
├── hosts/                        # Host-specific implementations
│   ├── WordAddIn/                # Windows Word VSTO (existing)
│   ├── WordVstoAddIn/            # Windows Word VSTO shell (existing)
│   ├── PowerPointAddIn/          # Windows PowerPoint VSTO (existing)
│   ├── PowerPointVstoAddIn/      # Windows PowerPoint VSTO shell (existing)
│   ├── OleFormulaObjectNative/   # OLE handler (existing)
│   │
│   ├── WpsAddIn/                 # 🆕 WPS Windows Add-in (JSAPI)
│   │   ├── wps.plugin.xml        # Plugin manifest
│   │   ├── src/
│   │   │   ├── index.html        # Task Pane entry
│   │   │   ├── main.js           # Plugin initialization
│   │   │   ├── taskpane.html     # Task Pane UI
│   │   │   ├── taskpane.js       # Task Pane logic
│   │   │   └── styles.css        # Styles
│   │   └── assets/
│   │       └── icons/
│   │
│   ├── OfficeMacAddIn/           # 🆕 Microsoft Office macOS Add-in
│   │   ├── manifest.xml          # Office Add-in manifest
│   │   ├── src/
│   │   │   ├── index.html        # Task Pane entry
│   │   │   ├── taskpane.html     # Task Pane UI
│   │   │   ├── taskpane.js       # Task Pane logic (Office.js)
│   │   │   └── styles.css        # Styles
│   │   └── assets/
│   │       └── icons/
│   │
│   └── WpsMacAddIn/              # 🆕 WPS macOS Add-in (JSAPI)
│       ├── wps.plugin.xml        # Plugin manifest
│       └── src/                  # Same as WpsAddIn (cross-platform)
│
├── shared/                       # 🆕 Shared web assets (Hybrid Architecture)
│   ├── core/                     # Core logic (platform-agnostic)
│   │   ├── bridge-client.js      # HTTP Bridge client with fallback
│   │   ├── local-renderer.js     # Local KaTeX renderer (fallback)
│   │   ├── latex-parser.js       # LaTeX parser
│   │   ├── formula-renderer.js   # Formula renderer
│   │   └── i18n/                 # Internationalization resources
│   │       ├── en.json
│   │       └── zh.json
│   ├── ui/                       # Shared UI components
│   │   ├── mathlive-editor.js    # MathLive formula editor
│   │   ├── symbol-library.js     # Symbol library (18 categories)
│   │   ├── preview-panel.js      # Preview panel
│   │   └── settings-panel.js     # Settings panel
│   └── styles/                   # Shared styles
│       └── common.css
│
├── installer/                    # Existing installer
└── tools/                        # Existing tools
```

---

## Implementation Plan

### Phase 1: WPS Windows Add-in (Priority: High)

**Duration**: 2-3 weeks

**Tasks**:
1. Create WPS plugin project structure
2. Implement `wps.plugin.xml` manifest
3. Create Task Pane UI (reuse existing MathLive editor)
4. Implement WPS JS API integration
5. Add HTTP Bridge client for LaTeX conversion
6. Implement formula insertion (OMML/PNG)
7. Test with WPS Office Windows

**Deliverables**:
- `office_plugin/hosts/WpsAddIn/` directory
- WPS plugin package (`.wps` or directory)
- Documentation for WPS users

### Phase 2: Microsoft Office macOS Add-in (Priority: Medium)

**Duration**: 2-3 weeks

**Tasks**:
1. Create Office Add-in project structure
2. Implement Office Add-in manifest (`manifest.xml`)
3. Create Task Pane UI (reuse existing components)
4. Implement Office.js API integration
5. Add HTTP Bridge client
6. Implement formula insertion (PNG image)
7. Test with Microsoft Office macOS

**Deliverables**:
- `office_plugin/hosts/OfficeMacAddIn/` directory
- Office Add-in package
- Documentation for Mac users

### Phase 3: WPS macOS Add-in (Priority: Medium)

**Duration**: 1-2 weeks

**Tasks**:
1. Create WPS macOS plugin project structure
2. Implement `wps.plugin.xml` manifest
3. Reuse WPS Windows Task Pane UI
4. Test with WPS Office macOS
5. Handle platform-specific differences

**Deliverables**:
- `office_plugin/hosts/WpsMacAddIn/` directory
- WPS macOS plugin package
- Cross-platform documentation

### Phase 4: Shared Components & Polish (Priority: Low)

**Duration**: 1-2 weeks

**Tasks**:
1. Extract shared Task Pane components
2. Create unified build system
3. Add CI/CD for cross-platform testing
4. Update documentation
5. Create distribution packages

**Deliverables**:
- `office_plugin/shared/` directory
- Build scripts for all platforms
- Comprehensive documentation

---

## Technical Details

### WPS Plugin Manifest (`wps.plugin.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp xmlns="http://schemas.microsoft.com/office/appforoffice/1.0"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Id>com.latexsnipper.wps</Id>
  <Version>1.0.0</Version>
  <Provider>LaTeXSnipper</Provider>
  <DefaultLocale>zh-CN</DefaultLocale>
  <HostApplication Name="Wps">
    <Host Name="Wps.Document" />
    <Host Name="Wps.Presentation" />
  </HostApplication>
  <App>
    <Title>LaTeXSnipper</Title>
    <Description>Insert LaTeX formulas into WPS documents</Description>
    <AppVersion>1.0.0</AppVersion>
  </App>
</OfficeApp>
```

### Office Add-in Manifest (`manifest.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp xmlns="http://schemas.microsoft.com/office/appforoffice/1.0"
           xmlns:bt="http://schemas.microsoft.com/office/officeappbasictasks/1.0"
           xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
           mc:Ignorable="o"
           xmlns:o="http://schemas.microsoft.com/office/2014/officeapp">
  <Id>com.latexsnipper.office.mac</Id>
  <Version>1.0.0</Version>
  <ProviderName>LaTeXSnipper</ProviderName>
  <DefaultLocale>en-US</DefaultLocale>
  <DisplayName DefaultValue="LaTeXSnipper"/>
  <Description DefaultValue="Insert LaTeX formulas into Word and PowerPoint"/>
  <Hosts>
    <Host Name="Document"/>
    <Host Name="Presentation"/>
  </Hosts>
  <AppDomains>
    <AppDomain>https://www.office.com</AppDomain>
  </AppDomains>
  <Requirements>
    <Sets>
      <Set Name="WordApi" MinVersion="1.3"/>
      <Set Name="SlideApi" MinVersion="1.2"/>
    </Sets>
  </Requirements>
  <DefaultSettings>
    <SourceLocation DefaultValue="https://localhost:3000/taskpane.html"/>
  </DefaultSettings>
  <Permissions>ReadWriteDocument</Permissions>
</OfficeApp>
```

### Shared Bridge Client (`bridge-client.js`)

```javascript
class BridgeClient {
  constructor(baseUrl = 'http://127.0.0.1:28765') {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  async getConfig() {
    const response = await fetch(`${this.baseUrl}/config`);
    const data = await response.json();
    this.token = data.token;
    return data;
  }

  async convertLatex(latex, options = {}) {
    const { display = true, targets = ['omml', 'png'] } = options;
    
    const response = await fetch(`${this.baseUrl}/convert/latex`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ latex, display, targets })
    });
    
    return await response.json();
  }

  async render(latex, options = {}) {
    const { display = true, targetDpi = 192 } = options;
    
    const response = await fetch(`${this.baseUrl}/render`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ latex, display, targetDpi })
    });
    
    return await response.json();
  }
}
```

### WPS JS API Integration (`wps-integration.js`)

```javascript
class WpsIntegration {
  constructor() {
    this.app = window.Application;
  }

  getDocument() {
    return this.app.ActiveDocument;
  }

  getSelection() {
    return this.app.Selection;
  }

  async insertFormula(ommlXml) {
    const selection = this.getSelection();
    
    // Method 1: Insert OMML XML
    selection.Range.InsertXML(ommlXml);
    
    // Method 2: Insert as image (fallback)
    // selection.InlineShapes.AddPicture(imagePath, false, true);
  }

  async insertFormulaAsImage(imageBase64) {
    const selection = this.getSelection();
    const tempPath = await this.saveTempImage(imageBase64);
    
    selection.InlineShapes.AddPicture(tempPath, false, true);
    
    // Clean up temp file
    await this.deleteTempFile(tempPath);
  }

  async saveTempImage(base64Data) {
    // Save base64 image to temp file
    const fs = require('fs');
    const path = require('path');
    const os = require('os');
    
    const tempDir = os.tmpdir();
    const fileName = `latex_formula_${Date.now()}.png`;
    const filePath = path.join(tempDir, fileName);
    
    const buffer = Buffer.from(base64Data, 'base64');
    fs.writeFileSync(filePath, buffer);
    
    return filePath;
  }
}
```

### Office.js Integration (`office-integration.js`)

```javascript
class OfficeIntegration {
  async insertFormula(imageBase64) {
    await Word.run(async (context) => {
      const range = context.document.getSelection();
      
      // Insert as inline picture
      range.insertInlinePictureFromBase64(
        imageBase64,
        Word.InsertLocation.after
      );
      
      await context.sync();
    });
  }

  async insertFormulaAsHtml(htmlContent) {
    await Word.run(async (context) => {
      const range = context.document.getSelection();
      
      // Insert HTML content
      range.insertHtml(htmlContent, Word.InsertLocation.after);
      
      await context.sync();
    });
  }

  async insertFormulaAsOml(ommlXml) {
    await Word.run(async (context) => {
      const range = context.document.getSelection();
      
      // Insert OMML XML
      range.insertXml(ommlXml, Word.InsertLocation.after);
      
      await context.sync();
    });
  }
}
```

---

## Platform-Specific Considerations

### Windows WPS vs Microsoft Office

| Feature | WPS | Microsoft Office |
|---------|-----|------------------|
| Plugin Type | JSAPI Add-in | VSTO Add-in |
| UI Framework | HTML/CSS/JS | WinForms/WPF |
| API | WPS JS API | COM Automation |
| Formula Insertion | OMML/XML or Image | OLE/OMML/Image |
| OLE Support | Limited | Full |
| Deployment | Plugin package | Installer |

### macOS Microsoft Office vs WPS

| Feature | Microsoft Office | WPS |
|---------|------------------|-----|
| Plugin Type | Web Add-in | JSAPI Add-in |
| WebView | WKWebView (Safari) | Chromium |
| API | Office.js | WPS JS API |
| Formula Insertion | Image/HTML/XML | OMML/XML or Image |
| OLE Support | No | Limited |
| Deployment | Microsoft Store / Sideload | Plugin package |

### Cross-Platform Compatibility

**Shared Components**:
- Task Pane UI (HTML/CSS/JS)
- MathLive formula editor
- KaTeX preview rendering
- Bridge client library
- Symbol library

**Platform-Specific**:
- Plugin manifest (different formats)
- API integration layer
- Formula insertion method
- Deployment mechanism

---

## Testing Strategy

### Unit Tests

- Bridge client API calls
- LaTeX parsing and validation
- OMML/XML generation
- Image rendering

### Integration Tests

- WPS plugin loading
- Office Add-in loading
- Formula insertion (all platforms)
- Document save/load with formulas

### Manual Testing

- WPS Office Windows (latest version)
- WPS Office macOS (latest version)
- Microsoft Office macOS (latest version)
- Cross-platform formula compatibility

---

## Distribution

### WPS

1. **WPS Plugin Marketplace**: Upload to `open.wps.cn`
2. **Local Installation**: Package as `.wps` file
3. **Enterprise Distribution**: Internal plugin repository

### Microsoft Office macOS

1. **Microsoft AppSource**: Upload to Microsoft marketplace
2. **Sideload**: Development testing
3. **Admin Deployment**: Organization-wide deployment

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WPS JS API differences from Office.js | Medium | Create abstraction layer |
| OMML compatibility issues | High | Test extensively, fallback to PNG |
| macOS API limitations | Medium | Use Web Add-in approach |
| WebView differences | Low | Use standard web technologies |
| Plugin approval process | Low | Start early, follow guidelines |

---

## Success Criteria

1. ✅ WPS plugin works on Windows with Word and PowerPoint
2. ✅ Office Add-in works on macOS with Word and PowerPoint
3. ✅ WPS plugin works on macOS with Word and PowerPoint
4. ✅ Formula insertion works correctly on all platforms
5. ✅ Bridge communication works reliably
6. ✅ Documentation is complete and accurate
7. ✅ Distribution packages are ready

---

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: WPS Windows | 2-3 weeks | Week 1 | Week 3 |
| Phase 2: Office macOS | 2-3 weeks | Week 3 | Week 5 |
| Phase 3: WPS macOS | 1-2 weeks | Week 5 | Week 6 |
| Phase 4: Polish | 1-2 weeks | Week 6 | Week 8 |

**Total**: 6-8 weeks

---

## Resources

- [WPS Open Platform Documentation](https://open.wps.cn/docs/office/)
- [Office Add-ins Documentation](https://learn.microsoft.com/en-us/office/dev/add-ins/)
- [Office.js API Reference](https://learn.microsoft.com/en-us/javascript/api/officejs)
- [WPS JS API Reference](https://open.wps.cn/docs/jsapi/)
