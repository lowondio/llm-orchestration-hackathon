from flask import Blueprint, request, jsonify
from utils.rag_manager import RagManager
import traceback

router = Blueprint('rag', __name__)

@router.route('/rag/upload', methods=['POST'])
def upload_file():
    """Upload a TXT or PDF file to index in RAG Knowledge Base"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part in request"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No selected file"}), 400
            
        node_id = request.form.get('node_id')
        if not node_id:
            return jsonify({"status": "error", "message": "Missing node_id parameter"}), 400
            
        chunk_size = int(request.form.get('chunk_size', 500))
        chunk_overlap = int(request.form.get('chunk_overlap', 50))
        
        # Read file bytes
        file_bytes = file.read()
        
        # Index file
        file_meta = RagManager.add_file(
            node_id=node_id,
            filename=file.filename,
            file_bytes=file_bytes,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return jsonify({
            "status": "success",
            "message": "File indexed successfully",
            "file": file_meta
        }), 200
        
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500

@router.route('/rag/files/<node_id>', methods=['GET'])
def list_files(node_id: str):
    """List all indexed files for a given RAG node"""
    try:
        files = RagManager.list_files(node_id)
        return jsonify({
            "status": "success",
            "files": files
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@router.route('/rag/files/<node_id>/<file_id>', methods=['DELETE'])
def delete_file(node_id: str, file_id: str):
    """Delete an indexed file and its chunks"""
    try:
        success = RagManager.delete_file(node_id, file_id)
        if success:
            return jsonify({
                "status": "success",
                "message": "File deleted successfully"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "File not found or could not be deleted"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
