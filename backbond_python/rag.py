import os
import json
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class RAGSystem:
    def __init__(self, knowledge_base_path=None):
        """初始化RAG系统"""
        # 初始化嵌入模型
        self.embeddings = OpenAIEmbeddings(
            model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"]
        )
        
        # 初始化向量数据库
        self.vector_store = None
        self.knowledge_base_path = knowledge_base_path
        
        # 如果提供了知识库路径，则加载或构建知识库
        if knowledge_base_path and os.path.exists(knowledge_base_path):
            self.load_knowledge_base(knowledge_base_path)
    
    def build_knowledge_base(self, documents_path, db_path="knowledge_base"):
        """从文档构建知识库"""
        # 加载文档
        loader = DirectoryLoader(documents_path, glob="*.json", loader_cls=TextLoader)
        documents = loader.load()
        
        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)
        
        # 创建向量数据库
        self.vector_store = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory=db_path
        )
        
        self.knowledge_base_path = db_path
        print(f"知识库构建完成，存储在 {db_path}")
    
    def load_knowledge_base(self, db_path="knowledge_base"):
        """加载已有的知识库"""
        if os.path.exists(db_path):
            self.vector_store = Chroma(
                persist_directory=db_path,
                embedding_function=self.embeddings
            )
            self.knowledge_base_path = db_path
            print(f"知识库加载完成，路径: {db_path}")
        else:
            print(f"知识库不存在: {db_path}")
    
    def add_document(self, document_path):
        """向知识库添加单个文档"""
        if not self.vector_store:
            print("请先构建或加载知识库")
            return False
        
        # 加载文档
        loader = TextLoader(document_path)
        document = loader.load()
        
        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(document)
        
        # 添加到向量数据库
        self.vector_store.add_documents(splits)
        
        # 持久化
        if self.knowledge_base_path:
            self.vector_store.persist()
        
        print(f"文档添加完成: {document_path}")
        return True
    
    def retrieve(self, query, k=3):
        """从知识库检索相关文档"""
        if not self.vector_store:
            print("请先构建或加载知识库")
            return []
        
        # 检索相关文档
        results = self.vector_store.similarity_search(query, k=k)
        
        return results
    
    def generate_with_context(self, query, k=3):
        """结合检索结果生成回答"""
        # 检索相关文档
        results = self.retrieve(query, k=k)
        
        # 构建上下文
        context = "\n".join([doc.page_content for doc in results])
        
        # 构建提示
        prompt = ChatPromptTemplate.from_template("""
        请根据以下上下文回答用户的问题：
        
        上下文：
        {context}
        
        用户问题：{query}
        
        请基于上下文内容回答问题，确保回答准确、简洁。如果上下文没有相关信息，可以回答："根据我的知识库，没有找到相关信息。"
        """)
        
        # 初始化LLM
        llm = ChatOpenAI(
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"]
        )
        
        # 生成回答
        result = llm.invoke(prompt.format(context=context, query=query))
        
        return {
            "answer": result.content,
            "context": context,
            "retrieved_docs": [doc.metadata for doc in results]
        }

# 创建全局RAG系统实例
rag_system = RAGSystem()
