import tempfile
from pathlib import Path
from unittest import TestCase
from django.test import TestCase as DjangoTestCase
from rag.models import ReferenceResume
from rag.utils import (
    EmbeddingService,
    ChromaService,
    split_resume_into_sections,
    chunk_section_content,
)


class RAGPipelineTest(TestCase):
    def test_split_resume_into_sections(self):
        resume_text = """
JOHN DOE
Computer Science Student

EDUCATION
IIT Bombay - CSE - CPI: 9.8

KEY PROJECTS
Road Accident Prevention
• Built a deep learning model.
• Reduced accident rates by 30%.

POSITIONS OF RESPONSIBILITY
Manager, DevCom
• Led a team of 15 developers.
"""
        sections = split_resume_into_sections(resume_text)
        self.assertIn("education", sections)
        self.assertIn("key_projects", sections)
        self.assertIn("positions_of_responsibility", sections)
        self.assertIn("IIT Bombay", sections["education"])
        self.assertIn("Road Accident Prevention", sections["key_projects"])
        self.assertIn("Manager, DevCom", sections["positions_of_responsibility"])

    def test_chunk_section_content_projects(self):
        projects_text = """Road Accident Prevention
• Built a deep learning model.
• Reduced accident rates by 30%.

Web App Builder
• Created backend with Django.
• Deployed to AWS.
"""
        chunks = chunk_section_content("key_projects", projects_text)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["entry_title"], "Road Accident Prevention")
        self.assertIn("Reduced accident rates", chunks[0]["content"])
        self.assertEqual(chunks[1]["entry_title"], "Web App Builder")
        self.assertIn("Deployed to AWS", chunks[1]["content"])

    def test_chunk_section_content_skills(self):
        skills_text = "Languages: Python, C++, Java\n\nFrameworks: Django, React"
        chunks = chunk_section_content("technical_skills", skills_text)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["entry_title"], "Technical_skills Block 1")
        self.assertEqual(chunks[0]["content"], "Languages: Python, C++, Java")


class DjangoRAGPipelineTest(DjangoTestCase):
    def test_local_embeddings_and_chroma(self):
        # 1. Test Embedding Service (all-MiniLM-L6-v2 produces 384 dimensions)
        embed_service = EmbeddingService()
        vector = embed_service.embed("test sentence")
        self.assertEqual(len(vector), 384)

        # 2. Test ChromaDB Service Ingestion and Queries
        chroma_service = ChromaService()
        
        test_ids = ["test_1", "test_2"]
        test_docs = [
            "Deep learning projects on image recognition",
            "Financial modeling for corporate strategy"
        ]
        test_embeddings = [
            embed_service.embed(test_docs[0]),
            embed_service.embed(test_docs[1])
        ]
        test_metadatas = [
            {"section_key": "key_projects", "company": "AILab"},
            {"section_key": "professional_experience", "company": "InvestCorp"}
        ]

        # Add
        chroma_service.add_chunks(
            ids=test_ids,
            documents=test_docs,
            embeddings=test_embeddings,
            metadatas=test_metadatas
        )

        # Query
        query_vector = embed_service.embed("machine learning image search")
        results = chroma_service.query_chunks(query_vector, n_results=1)

        self.assertEqual(len(results["ids"][0]), 1)
        # Should be closer to test_1 (deep learning/images) than test_2 (finance)
        self.assertEqual(results["ids"][0][0], "test_1")
        self.assertEqual(results["metadatas"][0][0]["company"], "AILab")
