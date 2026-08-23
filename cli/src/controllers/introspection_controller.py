"""Controller that maps parsed CLI arguments into introspection DTOs."""

import argparse
from typing import Any

from src.dto.requests import DescribeRequest, ScopeRequest, TablesRequest
from src.services.introspection_service import IntrospectionService


class IntrospectionController:
    def __init__(self, service: IntrospectionService | None = None) -> None:
        self.service = service or IntrospectionService()

    def execute(self, args: argparse.Namespace) -> Any:
        if args.command == "configurations": return self.service.configurations()
        if args.command == "connect": return self.service.connect(args.config_name)
        if args.command == "instances": return self.service.instances(ScopeRequest(config_name=args.config_name, no_cache=args.no_cache))
        if args.command == "schemas": return self.service.schemas(ScopeRequest(args.config_name, args.instance_name, args.no_cache))
        if args.command == "tables": return self.service.tables(TablesRequest(args.config_name, args.instance_name, args.no_cache, args.schema_name, args.limit, args.offset))
        return self.service.describe(DescribeRequest(args.config_name, args.instance_name, args.no_cache, args.schema_name, None, None, args.table_name, args.generate_ai_docs, args.save_metadata, args.only_if_changed))
