#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import pprint
import argparse
from apiclient.errors import HttpError

from const import *
from utils import *


def show_resource(resource):
    print "email:              %s" % resource['email']
    print "role:               %s" % resource['role']
    print "type:               %s" % resource['type']

def show_resource_list(resources, verbose):
    if verbose:
        print "etag: %s" % resources['etag']
        print "kind: %s" % resources['kind']
    if resources.has_key('members'):
        for resource in resources['members']:
            if verbose:
                show_resource(resource)
                print ""
            else:
                print "%s %s %s" % (resource['email'], resource['role'], resource['type'])

def list_member(sv, args):
    members = []
    pageToken = None

    params = { 'groupKey': args.groupKey }
    if args.role:
        params['roles'] = args.role

    while True:
        if pageToken:
            params['pageToken'] = pageToken

        status, r = execute_admin_api(sv.list(**params))
        if status == 404:
            sys.stderr.write('%s does not exist\n' % args.groupKey)
            sys.exit(2)

        if args.json or args.jsonPretty:
            if r.has_key('members'):
                for member in r['members']:
                    members.append(member)
        else:
            show_resource_list(r, args.verbose)

        if r.has_key('nextPageToken'):
            pageToken = r['nextPageToken']
        else:
            break

    if args.json or args.jsonPretty:
        if len(members) == 1:
           if args.jsonPretty:
               print to_pretty_json(members[0])
           elif args.json:
               print to_json(members[0])
        else:
           if args.jsonPretty:
               print to_pretty_json(members)
           elif args.json:
               print to_json(members)

def get_member(sv, args):
    status, r = execute_admin_api(sv.get(groupKey=args.groupKey, memberKey=args.memberKey))
    if status == 404:
        sys.stderr.write('%s does not exist\n' % args.groupKey)
        sys.exit(2)
    if args.jsonPretty:
        print to_pretty_json(r)
    elif args.json:
        print to_json(r)
    else:
        show_resource(r)

def insert_member(sv, args):
    body = { 'email': args.email, 'role': args.role }
    status, r = execute_admin_api(sv.insert(groupKey=args.groupKey, body=body))
    if status == 404:
        sys.stderr.write('%s does not exist\n' % args.groupKey)
        sys.exit(2)
    if args.verbose:
        if args.jsonPretty:
            print to_pretty_json(r)
        elif args.json:
            print to_json(r)
        else:
            show_resource(r)

def patch_member(sv, args):
    body = {}
    if args.role:
        body['role'] = args.role
    if len(body) > 0:
        status, r = execute_admin_api(sv.patch(groupKey=args.groupKey, memberKey=args.memberKey, body=body))
        if status == 404:
            sys.stderr.write('%s does not exist\n' % args.groupKey)
            sys.exit(2)
        if args.verbose:
            if args.jsonPretty:
                print to_pretty_json(r)
            elif args.json:
                print to_json(r)
            else:
                show_resource(r)
    else:
        print "no update column"

def delete_member(sv, args):
    status, r = execute_admin_api(sv.delete(groupKey=args.groupKey, memberKey=args.memberKey))
    if status == 404:
        sys.stderr.write('%s does not exist\n' % args.groupKey)
        sys.exit(2)

def bulk_insert_member(sv, args):
    f = open(args.jsonfile, 'r')
    members = json.load(f, 'utf-8')
    for member in members:
        groupKey = member['groupKey']
        del member['groupKey']
        try:
            status, r = execute_admin_api(sv.insert(groupKey=args.groupKey, body=member))
            if args.verbose:
                if args.jsonPretty:
                    print to_pretty_json(r)
                elif args.json:
                    print to_json(r)
                else:
                    show_resource(r)
        except HttpError, e:
            error = json.loads(e.content)
            code = error['error']['code']
            reason = error['error']['errors'][0]['reason']
            print "%s" %reason
            if code == 409 and reason  == "duplicate":
                print "%s already exist in group %s" %(member['email'], groupKey)
            elif code == 403 and reason  == "forbidden":
                print "%s could not be added into %s because %s" %(member['email'], groupKey, reason)
            else:
                print to_pretty_json(error)
                raise

def main():
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    subparsers = parser.add_subparsers(help='sub command')

    #-------------------------------------------------------------------------
    # LIST
    #-------------------------------------------------------------------------
    parser_list = subparsers.add_parser('list', help='Retrieves list of all members in a group')
    parser_list.add_argument('groupKey', help='group\'s email address, alias or the unique id')
    parser_list.add_argument('--role', choices=['OWNER', 'MANAGER', 'MEMBER'], help='role')
    parser_list.add_argument('-v', '--verbose', action='store_true', help='show all group data')
    parser_list.add_argument('--json', action='store_true', help='output json')
    parser_list.add_argument('--jsonPretty', action='store_true', help='output pretty json')
    parser_list.set_defaults(func=list_member)

    #-------------------------------------------------------------------------
    # GET
    #-------------------------------------------------------------------------
    parser_get = subparsers.add_parser('get', help='Retrieves a group member\'s properties')
    parser_get.add_argument('groupKey', help='group\'s email address, alias or the unique id')
    parser_get.add_argument('memberKey', help='member\'s email address')
    parser_get.add_argument('--json', action='store_true', help='output json')
    parser_get.add_argument('--jsonPretty', action='store_true', help='output pretty json')
    parser_get.set_defaults(func=get_member)

    #-------------------------------------------------------------------------
    # INSERT
    #-------------------------------------------------------------------------
    parser_insert = subparsers.add_parser('insert', help='Adds a user to the specified group')
    parser_insert.add_argument('groupKey', help='group\'s email address, alias or the unique id')
    parser_insert.add_argument('email', help='member\'s email address')
    parser_insert.add_argument('--role', choices=['OWNER', 'MANAGER', 'MEMBER'],
                               default='MEMBER', help='role of member')
    parser_insert.add_argument('-v', '--verbose', action='store_true',
                               help='show all group data')
    parser_insert.add_argument('--json', action='store_true', help='output json')
    parser_insert.add_argument('--jsonPretty', action='store_true', help='output pretty json')
    parser_insert.set_defaults(func=insert_member)

    #-------------------------------------------------------------------------
    # PATCH
    #-------------------------------------------------------------------------
    parser_patch = subparsers.add_parser('patch', help='Updates the membership properties of a user in the specified group')
    parser_patch.add_argument('groupKey', help='group\'s email address, alias or the unique id')
    parser_patch.add_argument('memberKey', help='member\'s email address')
    parser_patch.add_argument('--role', choices=['OWNER', 'MANAGER', 'MEMBER'], help='role')
    parser_patch.add_argument('-v', '--verbose', action='store_true', help='show all group data')
    parser_patch.add_argument('--json', action='store_true', help='output json')
    parser_patch.add_argument('--jsonPretty', action='store_true', help='output pretty json')
    parser_patch.set_defaults(func=patch_member)

    #-------------------------------------------------------------------------
    # DELETE
    #-------------------------------------------------------------------------
    parser_delete = subparsers.add_parser('delete', help='Removes a member from a group')
    parser_delete.add_argument('groupKey', help='group\'s email address, alias or the unique id')
    parser_delete.add_argument('memberKey', help='member\'s email address')
    parser_delete.set_defaults(func=delete_member)
    

    #
    # BULK insert
    #
    bulk_insert_member
    parser_bi = subparsers.add_parser('bulkinsert', help='bulk insert')
    parser_bi.add_argument('jsonfile')
    parser_bi.add_argument('-v', '--verbose', action='store_true', help='show inserted group data')
    parser_bi.add_argument('--json', action='store_true', help='output in JSON')
    parser_bi.add_argument('--jsonPretty', action='store_true', help='output in pretty JSON')
    parser_bi.set_defaults(func=bulk_insert_member)

    args = parser.parse_args()

    service = get_directory_service(args)

    args.func(service.members(), args)


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
    main()
