/*
 * Fusion2 webclient UX helpers.
 */
let fusion2Quickbar = (function () {
    var reconnecting = false;
    var nativeConfirm = window.confirm;

    var setStatus = function (state, label) {
        var status = $("#fusion-connection-status");
        var reconnect = $("#fusion-reconnect");

        if (!status.length) {
            return;
        }

        status.attr("data-state", state);
        status.find(".fusion-status-label").text(label || state);

        if (state === "disconnected" || state === "error") {
            reconnect.prop("hidden", false);
        } else {
            reconnect.prop("hidden", true);
        }
    };

    var sendCommand = function (command) {
        if (!command) {
            return;
        }
        plugin_handler.onSend(command);
        focusInput();
    };

    var focusInput = function () {
        var input = $(".inputfield.focused");
        if (!input.length) {
            input = $(".inputfield:last");
        }
        if (!input.length) {
            input = $("#inputfield");
        }
        input.focus();
    };

    var compactHeader = function () {
        var topbar = $(".fusion-client-topbar");
        var commandBar = $(".fusion-command-bar");
        var status = $("#fusion-connection-status");
        var toolbar = $("#toolbar");
        var controls = $(".fusion-client-controls");

        if (!topbar.length || !commandBar.length) {
            return;
        }

        if (!controls.length) {
            controls = $("<div>", { class: "fusion-client-controls" });
            topbar.append(controls);
        }

        if (!$.contains(topbar[0], commandBar[0])) {
            commandBar.insertBefore(controls);
        }
        if (status.length && !$.contains(controls[0], status[0])) {
            controls.prepend(status);
        }
        if (toolbar.length && !$.contains(controls[0], toolbar[0])) {
            controls.append(toolbar);
        }
    };

    var reconnect = function () {
        if (!window.Evennia || reconnecting) {
            return;
        }

        reconnecting = true;
        setStatus("reconnecting", "reconnecting");

        try {
            Evennia.connect();
        } finally {
            window.setTimeout(function () {
                reconnecting = false;
                if (!Evennia.isConnected()) {
                    setStatus("disconnected", "disconnected");
                }
            }, 1200);
        }
    };

    var bindControls = function () {
        $(".fusion-command-button").off("click.fusion2").on("click.fusion2", function (event) {
            sendCommand($(event.currentTarget).data("command"));
        });

        $("#fusion-reconnect").off("click.fusion2").on("click.fusion2", reconnect);
    };

    var interceptDisconnectedConfirm = function () {
        window.confirm = function (message) {
            if (message === "Not currently connected. Reconnect?") {
                setStatus("disconnected", "disconnected");
                return false;
            }
            return nativeConfirm.apply(window, arguments);
        };
    };

    var subscribeConnectionEvents = function () {
        if (!window.Evennia || !Evennia.emitter) {
            return;
        }

        Evennia.emitter.on("connection_open", function () {
            reconnecting = false;
            setStatus("connected", "connected");
        });
        Evennia.emitter.on("connection_error", function () {
            reconnecting = false;
            setStatus("error", "connection issue");
        });
    };

    var init = function () {
        compactHeader();
        bindControls();
        interceptDisconnectedConfirm();
        setStatus("connecting", "connecting");
    };

    var postInit = function () {
        subscribeConnectionEvents();
        if (window.Evennia && Evennia.isConnected()) {
            setStatus("connected", "connected");
        }
    };

    var onConnectionClose = function () {
        reconnecting = false;
        setStatus("disconnected", "disconnected");
    };

    return {
        init: init,
        postInit: postInit,
        onConnectionClose: onConnectionClose,
    };
})();

window.plugin_handler.add("fusion2_quickbar", fusion2Quickbar);
