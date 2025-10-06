from lxml import etree
from typing import Union
import os


def valid_xml_with_agt_xsd(xml_content: Union[bytes, str], xsd_path: str) -> Union[bool, str]:
    """
    Valida um conteúdo XML (string ou bytes) contra um XSD.

    Args:
        xml_content (Union[bytes, str]): Conteúdo do XML em formato string ou bytes.
        xsd_path (str): Caminho do arquivo XSD.

    Returns:
        bool | str: True se válido, ou string com mensagens de erro.
    """
    msg_error = ""
    try:
        # 1. Carregar o esquema XSD
        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f)
            schema = etree.XMLSchema(schema_doc)

        # 2. Converter para bytes se for string
        if isinstance(xml_content, str):
            xml_content = xml_content.encode('utf-8')

        # 3. Parsear o XML a partir do conteúdo
        xml_doc = etree.fromstring(xml_content)

        # 4. Validar
        schema.assertValid(xml_doc)
        return True

    except etree.DocumentInvalid as e:
        msg_error += "❌ Erros de validação encontrados:\n"
        for error in e.error_log:
            msg_error += f"- Linha {error.line}: {error.message}\n"
        return msg_error.strip()

    except etree.XMLSyntaxError as e:
        msg_error += f"❌ Erro de sintaxe no XML: {e}"
        return msg_error

    except Exception as e:
        msg_error += f"❌ Erro inesperado: {e}"
        return msg_error

# def get_xsd_file_path(self):
#     # Caminho absoluto até a pasta do módulo
#     module_path = os.path.dirname(os.path.abspath(__file__))
#
#     # Caminho até a raiz do módulo (voltar uma pasta para sair do "models")
#     module_root = os.path.dirname(module_path)
#
#     # Caminho completo para o ficheiro XSD
#     xsd_file_path = os.path.join(module_root, 'data', 'SAFTAO1.01_01.xsd')
#
# return xsd_file_path


# def get_xsd_file_path(self):
# module_path = Path(__file__).resolve().parent
#
# module_root = module_path.parent
#
# xsd_file_path = module_root / 'data' / 'SAFTAO1.01_01.xsd'
#
# return str(xsd_file_path)