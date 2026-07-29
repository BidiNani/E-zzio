class MemoryPolicy:


    MIN_TRUST=50


    @classmethod
    def accept(cls,score):

        return score >= cls.MIN_TRUST


    @classmethod
    def action(cls,score):

        if score>=80:
            return "KEEP"

        if score>=50:
            return "REVIEW"

        return "QUARANTINE"
