/* Shop assistant widget.
 *
 * Plain JavaScript, no build step and no external library. The whole
 * conversation is kept in sessionStorage because the shop is a multi-page
 * site: clicking a product card reloads the page, and without this the chat
 * would reset every time the customer followed a link.
 */
(function () {
    "use strict";

    var root = document.getElementById("shopbot");
    if (!root) {
        return;
    }

    var log = root.querySelector("[data-shopbot-log]");
    var form = root.querySelector("[data-shopbot-form]");
    var input = root.querySelector("[data-shopbot-input]");
    var sendBtn = root.querySelector("[data-shopbot-send]");
    var chipBar = root.querySelector("[data-shopbot-chips]");
    var launcher = root.querySelector("[data-shopbot-launcher]");
    var minimise = root.querySelector("[data-shopbot-minimise]");
    var csrfField = root.querySelector("[name=csrfmiddlewaretoken]");

    var askUrl = root.dataset.askUrl;
    var welcomeUrl = root.dataset.welcomeUrl;

    var STORE_KEY = "shopbot.transcript";
    var OPEN_KEY = "shopbot.open";
    var MAX_STORED = 40;

    var busy = false;

    /* ---------------------------------------------------------------- utils */

    function escapeHtml(text) {
        var div = document.createElement("div");
        div.textContent = text == null ? "" : String(text);
        return div.innerHTML;
    }

    /* The server sends plain text with a little **bold** and *italic*.
       Escape first, then add the markup, so a message can never inject HTML. */
    function formatText(text) {
        return escapeHtml(text)
            .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
            .replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>")
            .replace(/\n/g, "<br>");
    }

    function scrollToEnd() {
        log.scrollTop = log.scrollHeight;
    }

    function readStore(key, fallback) {
        try {
            var raw = window.sessionStorage.getItem(key);
            return raw ? JSON.parse(raw) : fallback;
        } catch (err) {
            return fallback;
        }
    }

    function writeStore(key, value) {
        try {
            window.sessionStorage.setItem(key, JSON.stringify(value));
        } catch (err) {
            /* Private browsing or a full quota — the chat still works,
               it just will not survive the next page load. */
        }
    }

    function remember(entry) {
        var transcript = readStore(STORE_KEY, []);
        transcript.push(entry);
        writeStore(STORE_KEY, transcript.slice(-MAX_STORED));
    }

    /* -------------------------------------------------------------- render */

    function addUserMessage(text, store) {
        var wrap = document.createElement("div");
        wrap.className = "shopbot-msg from-user";
        wrap.innerHTML = '<div class="shopbot-bubble">' + escapeHtml(text) + "</div>";
        log.appendChild(wrap);
        scrollToEnd();
        if (store !== false) {
            remember({ role: "user", text: text });
        }
    }

    function buildCard(card) {
        var link = document.createElement("a");
        link.className = "shopbot-card";
        link.href = card.url || "#";

        var img = "";
        if (card.image) {
            img = '<img class="shopbot-card-img" src="' + escapeHtml(card.image) +
                '" alt="" onerror="this.style.visibility=\'hidden\'">';
        } else {
            img = '<span class="shopbot-card-img"></span>';
        }

        var price = "";
        if (card.price) {
            price = '<span class="shopbot-card-price">' + escapeHtml(card.price) + "</span>";
            if (card.old_price) {
                price += '<span class="shopbot-card-old">' + escapeHtml(card.old_price) + "</span>";
            }
        }

        var badge = card.badge
            ? '<span class="shopbot-badge">' + escapeHtml(card.badge) + "</span>"
            : "";

        link.innerHTML =
            img +
            '<span class="shopbot-card-body">' +
            '<span class="shopbot-card-title">' + escapeHtml(card.title) + "</span>" +
            '<span class="shopbot-card-meta">' + escapeHtml(card.meta || "") + "</span>" +
            price + badge +
            "</span>";
        return link;
    }

    function addBotMessage(data, store) {
        if (data.reply) {
            var wrap = document.createElement("div");
            wrap.className = "shopbot-msg";
            wrap.innerHTML = '<div class="shopbot-bubble">' + formatText(data.reply) + "</div>";
            log.appendChild(wrap);
        }

        if (data.cards && data.cards.length) {
            var cards = document.createElement("div");
            cards.className = "shopbot-cards";
            data.cards.forEach(function (card) {
                cards.appendChild(buildCard(card));
            });
            log.appendChild(cards);
        }

        if (data.links && data.links.length) {
            var links = document.createElement("div");
            links.className = "shopbot-links";
            data.links.forEach(function (item) {
                var a = document.createElement("a");
                a.className = "shopbot-link";
                a.href = item.url;
                a.textContent = item.label;
                links.appendChild(a);
            });
            log.appendChild(links);
        }

        renderChips(data.chips || []);
        scrollToEnd();

        if (store !== false) {
            remember({ role: "bot", data: data });
        }
    }

    function renderChips(chips) {
        chipBar.innerHTML = "";
        chips.forEach(function (label) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "shopbot-chip";
            button.textContent = label;
            button.addEventListener("click", function () {
                send(label);
            });
            chipBar.appendChild(button);
        });
    }

    function showTyping() {
        var wrap = document.createElement("div");
        wrap.className = "shopbot-msg";
        wrap.setAttribute("data-typing", "");
        wrap.innerHTML =
            '<div class="shopbot-bubble"><span class="shopbot-typing">' +
            "<i></i><i></i><i></i></span></div>";
        log.appendChild(wrap);
        scrollToEnd();
        return wrap;
    }

    /* ------------------------------------------------------------ transport */

    function send(message) {
        var text = (message || "").trim();
        if (!text || busy) {
            return;
        }

        busy = true;
        sendBtn.disabled = true;
        input.value = "";
        addUserMessage(text);
        chipBar.innerHTML = "";

        var typing = showTyping();

        fetch(askUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfField ? csrfField.value : "",
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify({ message: text })
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                typing.remove();
                addBotMessage(data);
            })
            .catch(function () {
                typing.remove();
                addBotMessage({
                    reply: "Sorry, I could not reach the shop just now. " +
                        "Please check your connection and try again.",
                    chips: ["What is on sale?", "How long is delivery?"]
                });
            })
            .then(function () {
                busy = false;
                sendBtn.disabled = false;
                if (root.classList.contains("is-open")) {
                    input.focus();
                }
            });
    }

    /* --------------------------------------------------------------- panel */

    function restore() {
        var transcript = readStore(STORE_KEY, []);
        if (!transcript.length) {
            return false;
        }
        transcript.forEach(function (entry) {
            if (entry.role === "user") {
                addUserMessage(entry.text, false);
            } else {
                addBotMessage(entry.data, false);
            }
        });
        scrollToEnd();
        return true;
    }

    function greet() {
        var typing = showTyping();
        fetch(welcomeUrl, { credentials: "same-origin" })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                typing.remove();
                addBotMessage(data);
            })
            .catch(function () {
                typing.remove();
                addBotMessage({
                    reply: "Hello! Ask me about our products, prices, " +
                        "vendors or delivery.",
                    chips: ["What is on sale?", "What categories do you have?"]
                });
            });
    }

    function open() {
        root.classList.add("is-open");
        writeStore(OPEN_KEY, true);
        if (!log.children.length && !restore()) {
            greet();
        }
        scrollToEnd();
        window.setTimeout(function () {
            input.focus();
        }, 220);
    }

    function close() {
        root.classList.remove("is-open");
        writeStore(OPEN_KEY, false);
    }

    launcher.addEventListener("click", function () {
        if (root.classList.contains("is-open")) {
            close();
        } else {
            open();
        }
    });

    minimise.addEventListener("click", close);

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        send(input.value);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && root.classList.contains("is-open")) {
            close();
        }
    });

    /* Reopen automatically after a page navigation if it was open before,
       so following a product card does not close the conversation. */
    if (readStore(OPEN_KEY, false) === true) {
        restore();
        root.classList.add("is-open");
        scrollToEnd();
    }
})();
