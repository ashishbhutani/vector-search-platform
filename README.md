1. We have to implement HNSW algorithm (Hierarchical Navigable Small World graphs) in python
2. arxiv: https://arxiv.org/pdf/1603.09320
3. simpler explanantion: https://www.pinecone.io/learn/series/faiss/hnsw/
4. Why do we need to do that ? eventually i want to create a vector DB. this will
be one of the algorithm supported by the vector DB. but we will add more algos.
5. We want a simpler implenentation, clean and easy to read even if not the
   most efficient.
6. we will like to have test cases to check functionality with different inputs
7. we will like to have test cases to compare its precision/recall against
   a golden data set i.e. comparing approximate nearest neighbour search result
to a brute force search or kNN
8. we will like to have benchmarking of time taken to insert vectors, single or
   batch and time taken to retrieve.
9. we will like to have capability to insert new vectors without doing
   a rebuild
10. we will like to have option for different distance types or vector
    similarity functions


