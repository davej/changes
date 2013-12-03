from __future__ import absolute_import, division, unicode_literals

from flask import Response, request

from changes.api.base import APIView
from changes.models import LogSource, LogChunk


LOG_BATCH_SIZE = 50000  # in length of chars


class BuildLogDetailsAPIView(APIView):
    def get(self, build_id, source_id):
        """
        Return chunks for a LogSource.
        """
        source = LogSource.query.get(source_id)
        if source is None or source.build_id.hex != build_id:
            return Response(status=404)

        offset = int(request.args.get('offset', -1))
        limit = int(request.args.get('limit', LOG_BATCH_SIZE))

        queryset = LogChunk.query.filter(
            LogChunk.source_id == source.id,
        ).order_by(LogChunk.offset.desc())

        if offset == -1:
            # starting from the end so we need to know total size
            tail = queryset.limit(1).first()

            if tail is None:
                logchunks = []
            else:
                if limit:
                    queryset = queryset.filter(
                        (LogChunk.offset + LogChunk.size) >= max(tail.offset + tail.size - limit, 0),
                    )
                logchunks = list(queryset)
        else:
            queryset = queryset.filter(
                (LogChunk.offset + LogChunk.size) >= offset,
            )
            if limit:
                queryset = queryset.filter(
                    LogChunk.offset <= offset + limit,
                )
            logchunks = list(queryset)

        logchunks.sort(key=lambda x: x.date_created)

        return self.respond({
            'source': source,
            'chunks': logchunks,
            'nextOffset': logchunks[-1].offset + logchunks[-1].size,
        })

    def get_stream_channels(self, build_id, source_id):
        source = LogSource.query.get(source_id)
        if source is None or source.build_id.hex != build_id:
            return Response(status=404)

        return ['logsources:{0}:{1}'.format(build_id, source.id.hex)]
