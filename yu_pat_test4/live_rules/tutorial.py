"""
Tutorial controller stub.
Returns an inactive tutorial state — the full tutorial is a future feature.
"""

TUTORIAL_SEED = 42


class TutorialController:
    def dismiss(self):
        pass

    def tick(self, p1, p2, turn, hq_markers) -> dict:
        return {"active": False}


def new_tutorial() -> TutorialController:
    return TutorialController()
