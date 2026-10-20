FROM odoo:15.0

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true

COPY ./addons /mnt/extra-addons

USER odoo

# Força a atualização de todos os módulos e inicializa tabelas pendentes como payment_acquirer
CMD ["odoo", "-d", "ferranexus_db_9lxd", "-u", "all", "--without-demo=all", "--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons"]
