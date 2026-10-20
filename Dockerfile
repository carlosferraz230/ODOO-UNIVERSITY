FROM odoo:15.0

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true

COPY ./addons /mnt/extra-addons

USER odoo

# Força a migração do módulo account e a atualização do modelo res_company
CMD ["odoo", "-d", "ferranexus_db_9lxd", "-u", "account,web_enterprise", "--without-demo=all", "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"]
