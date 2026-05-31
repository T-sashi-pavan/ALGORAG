import os
import sys

# Force USE_CLOUD_EMBEDDINGS to true BEFORE importing BGEEmbeddings
# to prevent it from attempting to download/load the local SentenceTransformer model.
os.environ["USE_CLOUD_EMBEDDINGS"] = "true"

import numpy as np

# Ensure backend root is on Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embeddings.bge import BGEEmbeddings

def test_pooling():
    print("==================================================")
    print("TESTING MEAN POOLING MATHEMATICAL INTEGRITY (FAST)")
    print("==================================================")
    
    # Initialize embeddings (runs in offline/cloud mode immediately, zero load time)
    embeddings = BGEEmbeddings()
    
    # Mock data 1: Unpooled single text (Depth 2: shape [seq_len=3, dim=4])
    # Representing three token embeddings of size 4
    unpooled_single = [
        [1.0, 2.0, 3.0, 4.0],
        [2.0, 3.0, 4.0, 5.0],
        [3.0, 4.0, 5.0, 6.0]
    ]
    
    # The mean of each column is:
    # Col 0: (1+2+3)/3 = 2.0
    # Col 1: (2+3+4)/3 = 3.0
    # Col 2: (3+4+5)/3 = 4.0
    # Col 3: (4+5+6)/3 = 5.0
    # Expected mean pooled vector: [2.0, 3.0, 4.0, 5.0]
    
    print("\n[Test 1] Single Text (Depth 2) Pooling...")
    pooled_single = embeddings._pool_response(unpooled_single, expect_batch=False)
    print(f"-> Input shape: 3 tokens of size 4")
    print(f"-> Pooled single output: {pooled_single}")
    expected_single = [2.0, 3.0, 4.0, 5.0]
    assert np.allclose(pooled_single, expected_single), f"Failed single pooling! Expected {expected_single}, got {pooled_single}"
    print("-> [PASS] Single pooling matches expected mean vector!")

    # Mock data 2: Unpooled batch (Depth 3: shape [batch=2, seq_len=3, dim=4])
    unpooled_batch = [
        # Doc 1
        [
            [1.0, 2.0, 3.0, 4.0],
            [2.0, 3.0, 4.0, 5.0],
            [3.0, 4.0, 5.0, 6.0]
        ],
        # Doc 2
        [
            [10.0, 20.0, 30.0, 40.0],
            [20.0, 30.0, 40.0, 50.0],
            [30.0, 40.0, 50.0, 60.0]
        ]
    ]
    # Expected mean pooled vectors:
    # Doc 1: [2.0, 3.0, 4.0, 5.0]
    # Doc 2: [20.0, 30.0, 40.0, 50.0]
    
    print("\n[Test 2] Batch Text (Depth 3) Pooling...")
    pooled_batch = embeddings._pool_response(unpooled_batch, expect_batch=True)
    print(f"-> Input shape: batch of 2, each has 3 tokens of size 4")
    print(f"-> Pooled batch output: {pooled_batch}")
    expected_batch = [
        [2.0, 3.0, 4.0, 5.0],
        [20.0, 30.0, 40.0, 50.0]
    ]
    assert np.allclose(pooled_batch, expected_batch), f"Failed batch pooling! Expected {expected_batch}, got {pooled_batch}"
    print("-> [PASS] Batch pooling matches expected mean vectors!")

    # Mock data 3: Already pooled batch (Depth 2: shape [batch=2, dim=4])
    already_pooled = [
        [5.0, 6.0, 7.0, 8.0],
        [15.0, 16.0, 17.0, 18.0]
    ]
    print("\n[Test 3] Already Pooled Batch (Depth 2) Parsing...")
    parsed_pooled = embeddings._pool_response(already_pooled, expect_batch=True)
    print(f"-> Parsed pooled output: {parsed_pooled}")
    assert np.allclose(parsed_pooled, already_pooled), f"Failed parsed pooled! Expected {already_pooled}, got {parsed_pooled}"
    print("-> [PASS] Already pooled parsing preserved data!")

    print("\n==================================================")
    print("SUCCESS! ALL MEAN-POOLING TESTS PASSED FLAWLESSLY!")
    print("==================================================")
    return True

if __name__ == "__main__":
    try:
        test_pooling()
        sys.exit(0)
    except AssertionError as ae:
        print(f"\n[FAIL] Assertion Error: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected Error: {e}")
        sys.exit(1)
