const fs = require('fs');
var opts = require("minimist")(process.argv.slice(2));

if (!opts.f || typeof opts.f !== "string") {
  console.log("use -f to specify your mapping.json path");
  return;
}


fs.readFile(opts.f, 'utf8', (err, data) => {
    if (err) {
        console.error('Error reading file:', err);
        return;
    }

    try {
        const mapping = JSON.parse(data);
        const codepoints = {};
        
        Object.entries(mapping).forEach(([code, aliases]) => {
            const codeValue = parseInt(code);
            aliases.forEach((name) => {
                codepoints[name] = codeValue;
            });
        });

        const sorted = Object.entries(codepoints).sort((a, b) => a[1] - b[1]);

        let output = "import sys\nimport os\n\nCODEPOINTS = {\n";
        
        sorted.forEach(([name, code]) => {
            const hexCode = code.toString(16).padStart(4, '0');
            output += `    '${name}': 0x${hexCode},\n`;
        });
        
        output += "}\n\n\nclass CodiconManager:\n    _instance = None\n    \n    def __new__(cls):\n        if cls._instance is None:\n            cls._instance = super().__new__(cls)\n            cls._instance._initialized = False\n            cls._instance.font_family = 'Segoe MDL2 Assets'\n        return cls._instance\n    \n    def init(self):\n        if self._initialized:\n            return\n        \n        self.font_path = os.path.join(os.path.dirname(__file__), 'codicon.ttf')\n        loaded_family = self._load_font()\n        if loaded_family:\n            self.font_family = loaded_family\n        self._initialized = True\n    \n    def _load_font(self):\n        try:\n            from PySide6.QtGui import QFontDatabase\n            font_id = QFontDatabase.addApplicationFont(self.font_path)\n            if font_id != -1:\n                families = QFontDatabase.applicationFontFamilies(font_id)\n                if families:\n                    return families[0]\n        except ImportError:\n            pass\n        return None\n    \n    def get_char(self, icon_name):\n        code = CODEPOINTS.get(icon_name)\n        if code:\n            return chr(code)\n        return '?'\n    \n    def get_font(self, size=14):\n        try:\n            from PySide6.QtGui import QFont\n            font = QFont(self.font_family, size)\n            return font\n        except ImportError:\n            return None\n    \n    def icon(self, icon_name, size=14):\n        return self.get_char(icon_name)\n    \n    def font(self, size=14):\n        return self.get_font(size)\n\n\ncodicon = CodiconManager()\n\n\ndef get_icon(icon_name):\n    return codicon.get_char(icon_name)\n\n\ndef get_icon_font(size=14):\n    return codicon.get_font(size)\n";

        const outputPath = opts.o || '../ui/icons/codicon.py';
        fs.writeFileSync(outputPath, output, 'utf8');
        console.log(`Successfully generated: ${outputPath}`);

    } catch (error) {
        console.error('Error parsing JSON:', error);
    }
});
