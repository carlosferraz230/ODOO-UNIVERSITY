FROM odoo:15.0

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true

COPY ./addons /mnt/extra-addons

USER odoo

CMD ["odoo", "-d", "ferranexus_db_9lxd", "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"]
