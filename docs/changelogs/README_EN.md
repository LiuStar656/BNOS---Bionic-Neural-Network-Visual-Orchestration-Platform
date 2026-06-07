# BNOS Changelog

> Select language version:
> - [中文更新日志 (Chinese)](./cn/README.md)
> - [English Changelog](./en/README.md)

---

## Architecture Description

This project uses a **"Single Index Page + Version-Separate MD Sub-Files"** architecture to manage changelogs:

### Core Features

✅ **Minimal Home Page**: Only version titles + native triangle fold buttons  
✅ **Dynamic Loading**: Click triangle to expand version summary, details via link jump  
✅ **Modular Decoupling**: Each date has independent folder, new versions only need to add files  
✅ **Bidirectional Sync**: Modify sub-files, index page auto-syncs  
✅ **Native Folding**: Uses `<details><summary>` native folding, no JS required  
✅ **Cross-Platform Compatible**: Works with VSCode / Static Sites / Documentation Sites / Knowledge Bases  

### File Structure

```
changelogs/
├── README.md          # This file (language selection entry)
├── README_EN.md       # English version of this file
├── cn/
│   ├── README.md      # Chinese main index (with fold triangles)
│   ├── INDEX.md       # Chinese date-based index
│   ├── 2026-06-07/
│   ├── 2026-06-06/
│   └── ...
└── en/
    ├── README.md      # English main index (with fold triangles)
    ├── INDEX.md       # English date-based index
    ├── 2026-06-07/
    ├── 2026-06-06/
    └── ...
```

### Usage

1. **Browse Changelog**: Select [Chinese](./cn/README.md) or [English](./en/README.md) version
2. **Expand Version Summary**: Click the triangle on the left of the date to expand
3. **View Details**: Click "View Full Update" to enter detailed page for that date
4. **Date-based Navigation**: Use INDEX.md for quick date-based navigation

### Version Management

- **Add New Version**: Add update files to corresponding date folder, no need to modify old code
- **Version Archiving**: Each date folder is independent, supports separate archiving and review
- **Version Iteration**: Fully decoupled, supports unlimited iterations for dozens or hundreds of versions

---

## Quick Start

🚀 **Start Browsing Now**:
- [Chinese Changelog](./cn/README.md)
- [English Changelog](./en/README.md)

📚 **Architecture Features**:
- Native triangle folding (no JS)
- Version summary display
- Link navigation to detailed content
- Modular independent files
- Cross-platform rendering compatible