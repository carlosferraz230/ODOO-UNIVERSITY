from odoo import models, fields, api


class Fleet(models.Model):
    _inherit = 'fleet.vehicle.model'

    # Estes campos já existem no odoo, apenas vamos colocar certas funcionalidades adicionais.
    vehicle_type = fields.Selection([
        ('car', 'Carro'),
        ('bike', 'Bicicleta'),
        ('truck', 'Caminhão'),
        ('motorcycle', 'Motocicleta'),
        ('plane', 'Avião'),
    ],
        string="Tipo de Veículo",
        required=True
    )
    color = fields.Selection([
        ('red', 'Vermelho'), ('black', 'Preto'), ('green', 'Verde'), ('blue', 'Azul'), ('white', 'Branco'),
        ('orange', 'Laranja'), ('brown', 'Castanho'), ('rox', 'Roxo'), ('rose', 'Rosa'), ('cream', 'Creme'),
        ('violet', 'Violeta'),
        ('black_blue', 'Azul Escuro'), ('green_black', 'Verde Escuro'),
    ], required=True)

    # Estes Campos não estão a ser usados, mas ao eliminar eles levantou-se um erro
    seats = fields.Integer(required=True)
    doors = fields.Integer(required=True)
    model_year = fields.Char(required=True)
    # Aqui terminou




