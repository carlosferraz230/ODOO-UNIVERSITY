odoo.define('change_language.language_switcher', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var rpc = require('web.rpc');

    var LanguageSwitcher = core.Class.extend({
        init: function() {
            this.render();
        },

        render: function() {
            var self = this;
            var lang_code = session.user_context.lang || 'pt_BR';

            // Criar item do systray
            var menu = $('<li class="o_language_switcher dropdown">' +
                            '<a href="#" class="dropdown-toggle" data-toggle="dropdown">' +
                            '</a>' +
                            '<ul class="dropdown-menu dropdown-menu-right" id="language-switcher-menu"></ul>' +
                        '</li>');

            // Ícone da bandeira atual
            var img = $('<img>', {
                src: '/change_language/static/src/img/flags/' + lang_code + '.png',
                width: 20
            });
            menu.find('a').append(img);

            // Adiciona no systray
            $('.o_menu_systray').append(menu);

            // Carrega todos os idiomas disponíveis
            rpc.query({
                model: 'res.lang',
                method: 'search_read',
                args: [[], ['code','name']]
            }).then(function(langs){
                var ul = menu.find('#language-switcher-menu');
                langs.forEach(function(lang){
                    var li = $('<li><a href="#"><img src="/change_language/static/src/img/flags/' + lang.code + '.png" width="20" style="margin-right:5px;">' + lang.name + '</a></li>');
                    li.click(function(){
                        rpc.query({
                            model: 'res.users',
                            method: 'write',
                            args: [[session.uid], {lang: lang.code}]
                        }).then(function(){
                            location.reload();
                        });
                    });
                    ul.append(li);
                });
            });
        }
    });

    core.bus.on('web_client_ready', null, function(){
        new LanguageSwitcher();
    });
});
