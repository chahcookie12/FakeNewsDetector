# =============================================================
#  Test de propriété — Property 3 (task 3.3)
# =============================================================
#
#  Feature: database-persistence, Property 3: Format de date
#  canonique — For any date d'Article enregistrée, la date stockée
#  puis relue respecte exactement le format AAAA-MM-JJ HH:MM:SS et
#  correspond à la date d'origine formatée.
#
#  Validates: Requirements 2.3

import re
import uuid
from datetime import datetime

from hypothesis import given, settings, HealthCheck

from _db_helpers import ouvrir_base_temporaire, articles, resultats


# Expression régulière du format canonique AAAA-MM-JJ HH:MM:SS.
_FORMAT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(article=articles(), resultat=resultats())
def test_format_date_canonique(tmp_path, article, resultat):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        base.enregistrer_analyse(article, resultat)

        historique = base.recuperer_historique()
        assert len(historique) == 1
        date_relue = historique[0]["date"]

        # 1) La date relue respecte EXACTEMENT le format canonique.
        assert _FORMAT_DATE.match(date_relue)

        # 2) Elle correspond à la date d'origine formatée.
        attendue = article.date.strftime("%Y-%m-%d %H:%M:%S")
        assert date_relue == attendue

        # 3) Sécurité supplémentaire : la chaîne relue est bien
        #    ré-analysable selon ce même format.
        assert datetime.strptime(date_relue, "%Y-%m-%d %H:%M:%S") == \
            article.date.replace(microsecond=0)
    finally:
        base.fermer()
