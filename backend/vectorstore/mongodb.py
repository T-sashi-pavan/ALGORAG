import os
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import numpy as np

logger = logging.getLogger("algonox.vectorstore")

class MongoDBVectorStore:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI")
        self.db_name = "algonox_rag"
        self.collection_name = "document_chunks"
        
        if not self.uri:
            raise ValueError("MONGODB_URI is not set in environment variables.")
            
        try:
            import certifi
            self.client = MongoClient(self.uri, tlsCAFile=certifi.where(), tlsAllowInvalidCertificates=True, tls=True)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # Setup other required collections
            self.summaries_collection = self.db["document_summaries"]
            self.sessions_collection = self.db["chat_sessions"]
            self.messages_collection = self.db["messages"]
            self.files_collection = self.db["uploaded_files"]
            
            # Setup priority & email workflow collections
            self.priority_documents = self.db["priority_documents"]
            self.document_rankings = self.db["document_rankings"]
            self.email_logs = self.db["email_logs"]
            self.mail_delivery_status = self.db["mail_delivery_status"]
            self.selected_documents = self.db["selected_documents"]
            self.review_actions = self.db["review_actions"]
            
            logger.info("Successfully connected to MongoDB Atlas and initialized all collections.")
            
            # Try to build basic ascending indices for high performance metadata queries
            self.collection.create_index("document_id")
            self.collection.create_index("filename")
            self.files_collection.create_index("document_id")
            self.summaries_collection.create_index("document_id")
            self.sessions_collection.create_index("created_at")
            self.messages_collection.create_index("session_id")
            
            self.priority_documents.create_index("document_id")
            self.email_logs.create_index("sent_at")
            self.mail_delivery_status.create_index("delivery_id")
        except Exception as e:
            logger.error(f"Failed to connect or initialize MongoDB indexes: {e}")
            raise e

    def insert_chunks(self, chunks):
        """
        chunks: List of dicts, each having:
          - text: string
          - embedding: list of floats
          - metadata: dict with (filename, page, document_id, section, etc.)
        """
        if not chunks:
            return 0
        try:
            result = self.collection.insert_many(chunks)
            logger.info(f"Successfully inserted {len(result.inserted_ids)} chunks into MongoDB.")
            return len(result.inserted_ids)
        except PyMongoError as e:
            logger.error(f"Error inserting chunks into MongoDB: {e}")
            return 0

    def get_all_documents(self):
        """
        Returns unique document metadata. 
        Primary source: uploaded_files collection. Fallback: Aggregate chunk collection.
        """
        try:
            # Query the uploaded_files collection
            files = list(self.files_collection.find({}))
            if files:
                result = []
                for f in files:
                    # Defensive lookup for pages and other metadata
                    doc_id = f.get("document_id") or f.get("_id")
                    # Count chunks
                    chunk_count = self.collection.count_documents({"document_id": doc_id})
                    result.append({
                        "_id": doc_id,
                        "document_id": doc_id,
                        "filename": f.get("filename", "Untitled Document"),
                        "chunk_count": chunk_count,
                        "created_at": f.get("created_at", ""),
                        "page_count": f.get("page_count", 0),
                        "file_type": f.get("file_type", "")
                    })
                return result
        except Exception as e:
            logger.warning(f"Failed to fetch from files_collection: {e}. Falling back to chunk aggregation...")

        try:
            pipeline = [
                {"$group": {
                    "_id": "$document_id",
                    "filename": {"$first": "$metadata.filename"},
                    "chunk_count": {"$sum": 1},
                    "created_at": {"$first": "$metadata.created_at"}
                }}
            ]
            return list(self.collection.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Failed to aggregate documents: {e}")
            return []

    def delete_document(self, document_id):
        """
        Delete all chunks and files associated with a document_id
        """
        deleted_count = 0
        try:
            # Delete chunks
            result = self.collection.delete_many({"document_id": document_id})
            deleted_count = result.deleted_count
            logger.info(f"Deleted {deleted_count} chunks for document_id: {document_id}")
            
            # Delete from uploaded_files
            self.files_collection.delete_many({"$or": [{"document_id": document_id}, {"_id": document_id}]})
            
            # Delete summary
            self.summaries_collection.delete_many({"document_id": document_id})
            
            return deleted_count
        except PyMongoError as e:
            logger.error(f"Error deleting document: {e}")
            return 0

    # --- Uploaded Files helper methods ---
    def insert_uploaded_file(self, file_doc):
        try:
            self.files_collection.insert_one(file_doc)
            logger.info(f"Recorded uploaded file record: {file_doc.get('filename')}")
        except Exception as e:
            logger.error(f"Failed to insert uploaded file record: {e}")

    # --- Document Summary helper methods ---
    def insert_summary(self, summary_doc):
        try:
            # Check if exists, overwrite if so
            doc_id = summary_doc.get("document_id")
            if doc_id:
                self.summaries_collection.delete_many({"document_id": doc_id})
            self.summaries_collection.insert_one(summary_doc)
            logger.info(f"Stored document summary for doc: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to insert document summary: {e}")

    def get_summary(self, document_id):
        try:
            return self.summaries_collection.find_one({"document_id": document_id})
        except Exception as e:
            logger.error(f"Failed to get document summary: {e}")
            return None

    def get_summaries(self, document_ids=None):
        try:
            query = {}
            if document_ids:
                query = {"document_id": {"$in": document_ids}}
            return list(self.summaries_collection.find(query))
        except Exception as e:
            logger.error(f"Failed to get summaries: {e}")
            return []

    # --- Chat Sessions helper methods ---
    def create_chat_session(self, session_id, title, document_ids=None):
        try:
            import datetime
            session_doc = {
                "_id": session_id,
                "session_id": session_id,
                "title": title,
                "pinned": False,
                "document_ids": document_ids or [],
                "created_at": datetime.datetime.utcnow().isoformat(),
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
            self.sessions_collection.insert_one(session_doc)
            return session_doc
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            return None

    def get_chat_sessions(self):
        try:
            # Return all sessions sorted by updated_at or created_at descending
            return list(self.sessions_collection.find({}).sort([("pinned", -1), ("updated_at", -1)]))
        except Exception as e:
            logger.error(f"Failed to get chat sessions: {e}")
            return []

    def get_chat_session(self, session_id):
        try:
            return self.sessions_collection.find_one({"$or": [{"_id": session_id}, {"session_id": session_id}]})
        except Exception as e:
            logger.error(f"Failed to get chat session: {e}")
            return None

    def update_chat_session(self, session_id, title=None, pinned=None, document_ids=None):
        try:
            import datetime
            update_fields = {"updated_at": datetime.datetime.utcnow().isoformat()}
            if title is not None:
                update_fields["title"] = title
            if pinned is not None:
                update_fields["pinned"] = pinned
            if document_ids is not None:
                update_fields["document_ids"] = document_ids

            result = self.sessions_collection.update_one(
                {"$or": [{"_id": session_id}, {"session_id": session_id}]},
                {"$set": update_fields}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update chat session: {e}")
            return False

    def delete_chat_session(self, session_id):
        try:
            # Delete the session
            self.sessions_collection.delete_many({"$or": [{"_id": session_id}, {"session_id": session_id}]})
            # Also delete all messages in this session
            self.messages_collection.delete_many({"session_id": session_id})
            return True
        except Exception as e:
            logger.error(f"Failed to delete chat session: {e}")
            return False

    # --- Threaded Messages helper methods ---
    def insert_message(self, message_doc):
        try:
            self.messages_collection.insert_one(message_doc)
            # Update session's updated_at field
            session_id = message_doc.get("session_id")
            if session_id:
                self.update_chat_session(session_id)
            return True
        except Exception as e:
            logger.error(f"Failed to insert message: {e}")
            return False

    def get_messages(self, session_id):
        try:
            # Get all messages for a session, sorted by timestamp ascending
            return list(self.messages_collection.find({"session_id": session_id}).sort("timestamp", 1))
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []

    # --- Search functionality (Unchanged/Refined) ---
    def search(self, query_vector, limit=10, document_ids=None):
        """
        Perform vector search.
        Uses a robust fallback approach:
        Try MongoDB Vector Search `$vectorSearch` pipeline.
        If it errors (due to Search Index not being ready or fully registered),
        fall back to computing cosine similarity in-memory using loaded chunks.
        """
        results = []
        
        # Method A: Try standard Atlas Vector Search
        try:
            filter_clause = {}
            if document_ids:
                filter_clause = {"document_id": {"$in": document_ids}}
                
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": limit * 10,
                        "limit": limit
                    }
                }
            ]
            
            # Apply metadata filters if document_ids are provided
            if document_ids:
                pipeline[0]["$vectorSearch"]["filter"] = {"document_id": {"$in": document_ids}}
                
            cursor = self.collection.aggregate(pipeline)
            for doc in cursor:
                score = doc.get("score", doc.get("$vectorSearchScore", 0.8))
                results.append({
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": score,
                    "document_id": doc["document_id"]
                })
            
            if results:
                logger.info(f"Vector search returned {len(results)} matches via Atlas Vector Search.")
                return results
        except Exception as e:
            logger.warning(f"MongoDB Atlas $vectorSearch failed or vector_index is not active yet: {e}. Falling back to in-memory cosine similarity search...")

        # Method B: In-memory Cosine Similarity fallback (guarantees out-of-the-box operation!)
        try:
            match_query = {}
            if document_ids:
                match_query = {"document_id": {"$in": document_ids}}
                
            cursor = self.collection.find(match_query, {"text": 1, "embedding": 1, "metadata": 1, "document_id": 1}).limit(500)
            
            candidates = list(cursor)
            if not candidates:
                return []
                
            q_vec = np.array(query_vector)
            q_norm = np.linalg.norm(q_vec)
            
            scored_candidates = []
            for doc in candidates:
                if "embedding" not in doc or not doc["embedding"]:
                    continue
                d_vec = np.array(doc["embedding"])
                d_norm = np.linalg.norm(d_vec)
                if d_norm == 0 or q_norm == 0:
                    score = 0.0
                else:
                    score = float(np.dot(q_vec, d_vec) / (q_norm * d_norm))
                
                scored_candidates.append({
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": score,
                    "document_id": doc["document_id"]
                })
                
            scored_candidates.sort(key=lambda x: x["score"], reverse=True)
            results = scored_candidates[:limit]
            logger.info(f"Vector search returned {len(results)} matches via in-memory Cosine Similarity fallback.")
            return results
        except Exception as ex:
            logger.error(f"In-memory fallback search also failed: {ex}")
            return []

    # --- AI Priority & Email Delivery Helper Methods ---
    def save_priority_document(self, doc_data):
        try:
            doc_id = doc_data.get("document_id") or doc_data.get("_id")
            if doc_id:
                self.priority_documents.delete_many({"document_id": doc_id})
            self.priority_documents.insert_one(doc_data)
            return True
        except Exception as e:
            logger.error(f"Failed to insert priority document: {e}")
            return False

    def get_priority_documents(self):
        try:
            return list(self.priority_documents.find({}))
        except Exception as e:
            logger.error(f"Failed to get priority documents: {e}")
            return []

    def log_document_ranking(self, ranking_doc):
        try:
            self.document_rankings.insert_one(ranking_doc)
            return True
        except Exception as e:
            logger.error(f"Failed to log document ranking: {e}")
            return False

    def log_email(self, email_doc):
        try:
            self.email_logs.insert_one(email_doc)
            return True
        except Exception as e:
            logger.error(f"Failed to log email: {e}")
            return False

    def get_email_logs(self):
        try:
            logs = list(self.email_logs.find({}))
            # Serialize ObjectIds and dates to strings
            for log in logs:
                if "_id" in log:
                    log["_id"] = str(log["_id"])
            return logs
        except Exception as e:
            logger.error(f"Failed to fetch email logs: {e}")
            return []

    def log_delivery_status(self, delivery_doc):
        try:
            delivery_id = delivery_doc.get("delivery_id")
            if delivery_id:
                self.mail_delivery_status.delete_many({"delivery_id": delivery_id})
            self.mail_delivery_status.insert_one(delivery_doc)
            return True
        except Exception as e:
            logger.error(f"Failed to log delivery status: {e}")
            return False

    def update_delivery_status(self, delivery_id, status, error_message=None):
        try:
            import datetime
            update_fields = {
                "status": status,
                "updated_at": datetime.datetime.utcnow().isoformat()
            }
            if error_message:
                update_fields["error"] = error_message
            self.mail_delivery_status.update_one(
                {"delivery_id": delivery_id},
                {"$set": update_fields}
            )
            # Also update in email logs if matching
            self.email_logs.update_one(
                {"delivery_id": delivery_id},
                {"$set": {"status": status}}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update delivery status: {e}")
            return False

    def log_review_action(self, action_doc):
        try:
            self.review_actions.insert_one(action_doc)
            return True
        except Exception as e:
            logger.error(f"Failed to log review action: {e}")
            return False

