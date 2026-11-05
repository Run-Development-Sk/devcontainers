// Prettier config — .cjs format, so @prettier/plugin-xml can be loaded even
// in an isolated pre-commit node environment. require.resolve() finds the plugin in the
// node_modules of the given hook, so no wrapper or --plugin is needed on the CLI.
// The same approach is used by OCA (oca-addons-repo-template).
const config = {
    plugins: [require.resolve("@prettier/plugin-xml")],
    tabWidth: 4,
    printWidth: 100,
    bracketSameLine: true,
    overrides: [
        {
            files: "*.xml",
            options: {
                xmlWhitespaceSensitivity: "preserve",
                xmlSelfClosingSpace: false,
                xmlSortAttributesByKey: false,
            },
        },
        {
            files: "*.md",
            options: {
                tabWidth: 2,
                proseWrap: "preserve",
            },
        },
        {
            // Two-space indentation is the de-facto YAML standard (docker-compose,
            // GitHub Actions docs, yamllint default). Without this override YAML would
            // inherit the global tabWidth: 4.
            files: ["*.yml", "*.yaml"],
            options: {
                tabWidth: 2,
            },
        },
        {
            // Same for JSON: 2 spaces is the ecosystem default (npm, VS Code,
            // JSON.stringify(x, null, 2)) and what Odoo 20 CE uses for the spreadsheet
            // dashboard files that data/files/*.json here mirrors.
            files: "*.json",
            options: {
                tabWidth: 2,
            },
        },
    ],
};

module.exports = config;
