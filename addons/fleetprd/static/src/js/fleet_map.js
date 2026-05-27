odoo.define('fleet_map.live', function (require) {
    "use strict";

    var rpc = require('web.rpc');

    function initMap() {

        if (!document.getElementById('fleet_map')) {
            return;
        }

        var L = window.L;

        var map = L.map('fleet_map').setView([-8.8383, 13.2344], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
        }).addTo(map);

        var marker = null;

        async function loadLocation() {

            const data = await rpc.query({
                model: 'fleet.vehicle.location',
                method: 'search_read',
                args: [[], ['latitude', 'longitude']]
            });

            if (data.length > 0) {

                var last = data[0];

                if (marker) {
                    marker.setLatLng([last.latitude, last.longitude]);
                } else {
                    marker = L.marker([last.latitude, last.longitude]).addTo(map);
                }
            }
        }

        loadLocation();
        setInterval(loadLocation, 5000);
    }

    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(initMap, 1000);
    });

});