FROM odoo:15.0

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true

COPY ./addons /mnt/extra-addons

USER odoo

# Força o update dos módulos account e web para criar colunas e assets em falta
CMD ["odoo", "-d", "ferranexus_db_9lxd", "-u", "account,web,web_enterprise", "--without-demo=all", "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"]
