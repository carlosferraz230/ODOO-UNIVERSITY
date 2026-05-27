odoo.define('kudima_fleet.fleet_button_text', function (require) {
    "use strict";

    console.log("=== Fleet button patch ativo ===");

    function changeButtonText() {

        // filtra apenas contexto do Odoo (evita mexer em tudo)
        var buttons = document.querySelectorAll('.o_content button, .o_control_panel button');

        buttons.forEach(function (button) {

            var text = button.textContent.trim();

            if (text === 'Criar') {
                button.textContent = 'Cadastrar';
                button.setAttribute('title', 'Cadastrar registro');
                console.log("Botão alterado dinamicamente");
            }
        });
    }

    function startObserver() {

        var target = document.body;

        if (!target) return;

        var observer = new MutationObserver(function () {
            changeButtonText();
        });

        observer.observe(target, {
            childList: true,
            subtree: true
        });

        console.log("Observer ativo");
    }

    function init() {
        changeButtonText();   // primeira execução
        startObserver();      // depois fica reativo
    }

    $(document).ready(function () {
        init();
    });

});