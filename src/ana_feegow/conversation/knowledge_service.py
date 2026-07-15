from ana_feegow.conversation.knowledge_markdown import KnowledgeMarkdown


class KnowledgeService:

    @classmethod
    def get_document(cls):
        return KnowledgeMarkdown.load()

    @classmethod
    def search(cls, pergunta: str):
        return KnowledgeMarkdown.search(pergunta)
