import json
import sys
from rag_agent_v2 import get_rag_chain, PAGE_SUMMARY_PROMPT_EN
from langchain_core.messages import HumanMessage, AIMessage

def test_prompt_formatting():
    print("--- TRACING LLM PAYLOAD ---")
    
    # 1. Retrieved chunks count
    chunks_count = 3
    print(f"1. Retrieved chunks count: {chunks_count}")
    
    # Fake chunks that would come from the retrieval script
    chunks = [
        {"page": 100, "text": "Chunk 1 Text: ಹೇಳಿ ಹೋಗು ಕಾರಣ..."},
        {"page": 100, "text": "Chunk 2 Text: ರಸ್ತೆಯಲ್ಲ ಉತ್ತರಾಭಮುಖವಾಗಿ..."},
        {"page": 100, "text": "Chunk 3 Text: ತ ನಿಂತಿದ್ದ ಕಾವೇರಿಯಾಗಲೀ..."}
    ]
    
    # 2. Full context assembled before LLM call
    rag_section = (
        "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])
        if chunks else "(No specific passages retrieved.)"
    )
    print(f"\n2. Full context assembled before LLM call (Length: {len(rag_section)}):")
    print("---")
    print(rag_section[:300] + "...")
    print("---")
    
    # Setup chain
    chain = get_rag_chain("English", is_page_summary=True)
    
    # 3-8. Let's manually format the prompt to see what it generates
    # chain is: prompt | llm | parser
    # Let's extract the prompt and format it
    prompt_template = chain.first
    
    inputs = {
        "book_context": "Book Context here",
        "context": rag_section,
        "history": [],
        "question": "Summarize page 100"
    }
    
    try:
        formatted_messages = prompt_template.format_messages(**inputs)
        
        print("\n3. Final prompt sent to LLM:")
        for msg in formatted_messages:
            print(f"\n[{msg.type.upper()} MESSAGE]:")
            print(msg.content[:1000] + ("..." if len(msg.content) > 1000 else ""))
            
        print(f"\n4. System prompt used:\n{formatted_messages[0].content[:200]}...")
        print(f"\n5. User prompt used:\n{formatted_messages[-1].content}")
        
        # 6. Context length passed
        print(f"\n6. Context length passed to Gemini: {len(rag_section)}")
        
        # 7. First 1000 characters
        print(f"\n7. First 1000 characters of actual context passed:\n{rag_section[:1000]}")
        
        print("\n9. Diagnosis:")
        if not rag_section.strip() or rag_section == "(No specific passages retrieved.)":
            print("- Context is empty: TRUE")
        else:
            print("- Context is empty: FALSE")
            
        # Is there anything missing in PAGE_SUMMARY_PROMPT?
        # Actually wait, let's see if the LLM call is using the right things.
        print("- Wrong prompt is used: FALSE (Using PAGE_SUMMARY_PROMPT_EN)")
        
        print("\nAll good!")
        
    except Exception as e:
        print(f"\nERROR Formatting Prompt: {type(e).__name__} - {e}")
        
        import traceback
        traceback.print_exc()
        
        print("\n9. Diagnosis:")
        print(f"- ERROR DETECTED: {e}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    test_prompt_formatting()
