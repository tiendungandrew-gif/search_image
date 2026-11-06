import hashlib
import io


def object_key(image):
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[image.media_type]
    return f"images/original/{image.id}/{image.sha256}.{extension}"


async def get_original(services, image):
    def read():
        response = services.minio.client.get_object(services.minio.bucket, object_key(image))
        try:
            data = response.read(services.settings.image_max_upload_mb * 1024**2 + 1)
        finally:
            response.close()
            response.release_conn()
        if len(data) != image.byte_size or hashlib.sha256(data).hexdigest() != image.sha256:
            raise ValueError("OBJECT_DIGEST_MISMATCH")
        return data

    return await services.minio.run(read)


async def put_original(services, image, data):
    await services.minio.run(
        lambda: services.minio.client.put_object(
            services.minio.bucket,
            object_key(image),
            io.BytesIO(data),
            len(data),
            content_type=image.media_type,
        )
    )
    await get_original(services, image)
