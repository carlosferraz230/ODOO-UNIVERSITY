FROM odoo:15.0

USER root

COPY requirements.txt /tmp/requirements.txt

RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY ./addons /mnt/extra-addons
COPY ./addons-custom /mnt/addons-custom

USER odoo