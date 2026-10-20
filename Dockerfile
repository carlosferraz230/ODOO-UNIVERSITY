FROM odoo:15.0

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true

# Copia a pasta de addons do repositório
COPY ./addons /mnt/extra-addons

USER odoo

# Força o caminho dos addons e a atualização de todas as dependências
CMD ["odoo", "-d", "ferranexus_db_9lxd", "-u", "all", "--without-demo=all", "--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"]
