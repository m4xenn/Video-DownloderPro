"""Parse bounded remote manifests without DTDs, entities or external resources."""
from defusedxml.ElementTree import DefusedXMLParser
from xml.etree.ElementTree import TreeBuilder


class ManifestTree(TreeBuilder):
    def __init__(self):
        super().__init__();self.depth=0;self.nodes=0

    def start(self,tag,attrs):
        self.depth+=1;self.nodes+=1
        if self.depth>64 or self.nodes>100000 or len(attrs)>512:
            raise ValueError('XML manifest complexity limit')
        return super().start(tag,attrs)

    def end(self,tag):
        result=super().end(tag);self.depth-=1;return result


def parse_manifest(body):
    if not isinstance(body,(bytes,bytearray)) or len(body)>4*1024*1024:
        raise ValueError('XML manifest exceeds metadata budget')
    try:
        parser=DefusedXMLParser(target=ManifestTree(),forbid_dtd=True,forbid_entities=True,forbid_external=True)
        parser.feed(bytes(body))
        return parser.close()
    except Exception as exc:
        raise ValueError('Invalid or unsafe XML manifest') from exc
