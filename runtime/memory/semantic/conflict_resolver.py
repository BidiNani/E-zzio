class MemoryConflictResolver:


    @staticmethod
    def resolve(a,b):


        if a==b:

            return {
                "status":"IDENTICAL",
                "winner":a
            }


        return {

            "status":"CONFLICT",

            "candidates":[
                a,
                b
            ]

        }
