from src.repository.chunk_repo import get_chunk_repo

async def prepare_dataset():
    chunk_repo = await get_chunk_repo()
    dataset = []

    dataset_file_id = ['0ed6a366-1f72-4422-b77f-0528028233c8',
                           '70dc4644-701d-41eb-b86d-8ea195b26479',
                           'fa5f0faf-a445-4425-ae61-0dc032d546d2']

    for file_id in dataset_file_id:
        chunks = await chunk_repo.get_chunks_by_document_id(file_id)
        for chunk in chunks:
            chunk['id'] = str(chunk['id'])

        dataset.append({
            'document_id': file_id,
            'chunks': chunks
        })

    return dataset
