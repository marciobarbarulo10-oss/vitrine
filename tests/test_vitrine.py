"""Testes do motor de nota. Só biblioteca padrão: python -m unittest discover -s tests"""
import datetime as dt
import importlib.util
import os
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_modulo(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


os.environ["VITRINE_HOME"] = str(RAIZ / "exemplo")
os.environ["VITRINE_HOJE"] = "2026-01-05"
motor = carregar_modulo("vitrine", RAIZ / "skill" / "scripts" / "vitrine.py")
exportar = carregar_modulo("exportar", RAIZ / "painel" / "exportar.py")


class Casamento(unittest.TestCase):
    def test_palavra_inteira(self):
        self.assertTrue(motor.contem(motor.norm("uso Git todo dia"), "Git"))
        self.assertFalse(motor.contem(motor.norm("projetos no GitHub"), "Git"))

    def test_ignora_acento_e_maiuscula(self):
        self.assertTrue(motor.contem(motor.norm("AUTOMAÇÃO de processos"), "automacao"))

    def test_sinonimo_conta(self):
        termo = {"termo": "Git", "sinonimos": ["GitHub"]}
        self.assertTrue(motor.achou(motor.norm("projetos no GitHub"), termo))


class Peso(unittest.TestCase):
    def test_obrigatorio_vale_dobro(self):
        termo = {"termo": "SQL", "tipo": "hard", "vagas": ["v1", "v2"], "obrigatorio_em": ["v1"]}
        self.assertEqual(motor.peso_termo(termo), 3)

    def test_soft_vale_metade(self):
        termo = {"termo": "Comunicação", "tipo": "soft", "vagas": ["v1", "v2"], "obrigatorio_em": []}
        self.assertEqual(motor.peso_termo(termo), 1.0)


class Aderencia(unittest.TestCase):
    def test_taxa_e_o_peso_encontrado_sobre_o_total(self):
        perfil = {"headline": "Analista de dados", "sobre": "Uso SQL no dia a dia.", "competencias": []}
        vagas = {"vagas": [{"id": "v1"}], "termos": [
            {"termo": "SQL", "tipo": "hard", "vagas": ["v1"], "obrigatorio_em": ["v1"]},     # peso 2, presente
            {"termo": "Python", "tipo": "hard", "vagas": ["v1"], "obrigatorio_em": []},      # peso 1, ausente
            {"termo": "Power BI", "tipo": "hard", "vagas": ["v1"], "obrigatorio_em": []},    # peso 1, ausente
        ]}
        checagens, extra = motor.checar_aderencia(perfil, vagas)
        self.assertEqual(extra["taxa"], 0.5)
        self.assertEqual(extra["presentes"], ["SQL"])
        self.assertEqual(checagens[0]["pontos"], 12.0)  # metade dos 24 pontos

    def test_sem_perfil_nao_pontua(self):
        checagens, _ = motor.checar_aderencia(None, {"termos": [{"termo": "SQL"}]})
        self.assertEqual(sum(c["pontos"] for c in checagens), 0)


class Vitrine(unittest.TestCase):
    def test_repositorio_de_estudo_nao_conta(self):
        alvo = {"github_user": "fulano", "repos_estudo": ["estudos"]}
        gh = {"bio": "x", "blog": "", "readme_perfil_chars": 0, "repos": [
            {"nome": "projeto", "descricao": "faz algo", "licenca": "MIT", "topicos": [], "ultimo_push": "2026-01-01"},
            {"nome": "estudos", "descricao": None, "licenca": None, "topicos": [], "ultimo_push": "2020-01-01"},
        ]}
        por_id = {c["id"]: c for c in motor.checar_vitrine({}, gh, alvo)}
        self.assertEqual(por_id["repo_licenca"]["pontos"], por_id["repo_licenca"]["max"])
        self.assertEqual(por_id["repo_descricao"]["detalhe"], "1 de 1.")

    def test_sem_repositorio_de_vitrine(self):
        alvo = {"github_user": "fulano", "repos_estudo": ["estudos"]}
        gh = {"repos": [{"nome": "estudos"}]}
        por_id = {c["id"]: c for c in motor.checar_vitrine({}, gh, alvo)}
        self.assertEqual(por_id["repos"]["pontos"], 0)


class NotaDoExemplo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nota = motor.calcular()

    def test_total_e_a_soma_das_categorias(self):
        soma = round(sum(c["pontos"] for c in self.nota["categorias"].values()), 1)
        self.assertEqual(self.nota["total"], soma)
        self.assertTrue(0 <= self.nota["total"] <= 100)

    def test_nenhuma_categoria_passa_do_maximo(self):
        for cat in self.nota["categorias"].values():
            self.assertLessEqual(cat["pontos"], cat["max"], cat["nome"])
        self.assertEqual(sum(c["max"] for c in self.nota["categorias"].values()), 100)

    def test_maximos_das_checagens_fecham_com_a_categoria(self):
        for cid, _, maximo in motor.CATEGORIAS:
            soma = sum(c["max"] for c in self.nota["checagens"] if c["categoria"] == cid)
            self.assertAlmostEqual(soma, maximo, msg=cid)

    def test_mesma_entrada_mesma_nota(self):
        self.assertEqual(motor.calcular()["total"], self.nota["total"])

    def test_rotina_segue_o_dia_da_semana(self):
        self.assertEqual(motor.hoje(), dt.date(2026, 1, 5))  # uma segunda-feira
        self.assertEqual(motor.ROTINAS[motor.hoje().weekday()][0], "medir")


class Painel(unittest.TestCase):
    def test_checagem_vai_para_o_canal_certo(self):
        self.assertEqual(exportar.canal_grupo({"id": "repo_licenca", "categoria": "vitrine"}),
                         ("github", "Repositórios de vitrine"))
        self.assertEqual(exportar.canal_grupo({"id": "github_bio", "categoria": "vitrine"}),
                         ("github", "Perfil do GitHub"))
        self.assertEqual(exportar.canal_grupo({"id": "github_no_perfil", "categoria": "vitrine"}),
                         ("linkedin", "Projetos no LinkedIn"))
        self.assertEqual(exportar.canal_grupo({"id": "post_recente", "categoria": "atividade"}),
                         ("linkedin", "Atividade e rede"))


if __name__ == "__main__":
    unittest.main()
