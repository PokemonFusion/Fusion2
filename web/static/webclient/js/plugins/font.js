/*
 * Fusion2 webclient font options.
 *
 * This mirrors Evennia's stock font plugin while keeping the local Fira Mono
 * default and applying saved settings on startup.
 */
let font_plugin = (function () {

    const defaultFontFamily = "Fira Mono";
    const defaultFontSize = "0.9";

    const font_urls = {
        "B612 Mono": "https://fonts.googleapis.com/css?family=B612+Mono&display=swap",
        "Consolas": "https://fonts.googleapis.com/css?family=Consolas&display=swap",
        "DejaVu Sans Mono": "/static/webclient/fonts/DejaVuSansMono.css",
        "Fira Mono": "https://fonts.googleapis.com/css?family=Fira+Mono&display=swap",
        "Inconsolata": "https://fonts.googleapis.com/css?family=Inconsolata&display=swap",
        "Monospace": "",
        "Roboto Mono": "https://fonts.googleapis.com/css?family=Roboto+Mono&display=swap",
        "Source Code Pro": "https://fonts.googleapis.com/css?family=Source+Code+Pro&display=swap",
        "Ubuntu Mono": "https://fonts.googleapis.com/css?family=Ubuntu+Mono&display=swap",
    };

    var cssFontStack = function (family) {
        if (family === "Monospace") {
            return "monospace";
        }
        return "\"" + family.replace(/"/g, "\\\"") + "\", \"DejaVu Sans Mono\", Consolas, \"Lucida Console\", monospace";
    };

    var applyFontFamily = function (family) {
        var stack = cssFontStack(family);
        document.documentElement.style.setProperty("--fusion-terminal-font", stack);
        $(document.body).css("font-family", stack);
    };

    var applyFontSize = function (size) {
        document.documentElement.style.setProperty("--fusion-terminal-font-size", size + "rem");
        $(document.body).css("font-size", size + "rem");
    };

    var getActiveFontFamily = function () {
        return localStorage.getItem("evenniaFontFamily") || defaultFontFamily;
    };

    var getActiveFontSize = function () {
        return localStorage.getItem("evenniaFontSize") || defaultFontSize;
    };

    var setStartingFont = function () {
        applyFontFamily(getActiveFontFamily());
        applyFontSize(getActiveFontSize());
    };

    var onFontFamily = function (evnt) {
        var family = $(evnt.target).val();
        applyFontFamily(family);
        localStorage.setItem("evenniaFontFamily", family);
    };

    var onFontSize = function (evnt) {
        var size = $(evnt.target).val();
        applyFontSize(size);
        localStorage.setItem("evenniaFontSize", size);
    };

    var onOptionsUI = function (parentdiv) {
        var fontselect = $("<select>");
        var sizeselect = $("<select>");

        var fonts = Object.keys(font_urls);
        for (const font of fonts) {
            fontselect.append($("<option value='" + font + "'>" + font + "</option>"));
        }

        for (var x = 4; x < 21; x++) {
            var val = x / 10.0;
            sizeselect.append($("<option value='" + val + "'>" + x + "</option>"));
        }

        fontselect.val(getActiveFontFamily());
        sizeselect.val(getActiveFontSize());

        fontselect.on("change", onFontFamily);
        sizeselect.on("change", onFontSize);

        parentdiv.append("<div style='font-weight: bold'>Font Selection:</div>");
        parentdiv.append(fontselect);
        parentdiv.append(sizeselect);
    };

    var init = function () {
        var head = $(document.head);

        var fonts = Object.keys(font_urls);
        for (var x = 0; x < fonts.length; x++) {
            if (fonts[x] !== "Monospace") {
                var url = font_urls[fonts[x]];
                var link = $("<link href='" + url + "' rel='stylesheet'>");
                head.append(link);
            }
        }

        setStartingFont();
    };

    return {
        init: init,
        onOptionsUI: onOptionsUI,
    };
})();
window.plugin_handler.add("font", font_plugin);
