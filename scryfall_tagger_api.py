#!/usr/bin/env python3
"""
Scryfall Tagger API Client

Based on network traffic analysis of https://tagger.scryfall.com/card/m19/3

Key findings:
1. Page loads card data via GraphQL endpoint: https://tagger.scryfall.com/graphql
2. Requires CSRF token extracted from the initial page load
3. GraphQL query "FetchCard" returns card details + community tags
4. Tags include: artwork tags (dual wielding, roar, blue sky, etc.) and card tags (reanimate, support, etc.)
5. Each tag has metadata: creator, weight, status, description, ancestor tags

API ENDPOINT FOUND: https://tagger.scryfall.com/graphql
"""

import requests
import json
import re
from bs4 import BeautifulSoup

class ScryfallTaggerAPI:
    def __init__(self):
        self.base_url = "https://tagger.scryfall.com"
        self.session = requests.Session()
        self.csrf_token = None

        # Headers based on network capture
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://tagger.scryfall.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })

    def get_csrf_token(self, card_path="/card/m19/3"):
        """Extract CSRF token from page HTML"""
        url = f"{self.base_url}{card_path}"
        response = self.session.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to load page: {response.status_code}")

        # Extract CSRF token from meta tag
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})

        if not csrf_meta:
            raise Exception("CSRF token not found in page")

        self.csrf_token = csrf_meta['content']
        print(f"✓ Extracted CSRF token: {self.csrf_token[:20]}...")

        # Update session headers
        self.session.headers.update({
            'X-CSRF-Token': self.csrf_token,
            'Referer': url
        })

        return self.csrf_token

    def fetch_card_tags(self, card_set, collector_number, back=False, moderator_view=False):
        """
        Fetch card data and community tags via GraphQL

        Args:
            card_set: Magic set code (e.g., "m19")
            collector_number: Card number in set (e.g., "3")
            back: Whether to fetch backside of card (default False)
            moderator_view: Whether to include moderation data (default False)

        Returns:
            dict: Card data including tags, or None if failed
        """

        if not self.csrf_token:
            self.get_csrf_token(f"/card/{card_set}/{collector_number}")

        # GraphQL query from network capture
        query = """
        query FetchCard(
          $set: String!
          $number: String!
          $back: Boolean = false
          $moderatorView: Boolean = false
        ) {
          card: cardBySet(set: $set, number: $number, back: $back) {
            ...CardAttrs
            backside
            flipsideDisplayName
            hasAlternateName
            layout
            scryfallUrl
            sideNames
            twoSided
            rotatedLayout
            taggings(moderatorView: $moderatorView) {
              ...TaggingAttrs
              tag {
                ...TagAttrs
                ancestorTags {
                  ...TagAttrs
                }
              }
            }
            relationships(moderatorView: $moderatorView) {
              ...RelationshipAttrs
            }
          }
        }

        fragment CardAttrs on Card {
          artImageUrl
          backside
          cardImageUrl
          collectorNumber
          displayName
          id
          illustrationId
          layout
          name
          oracleId
          printingId
          set
          sideNames
        }

        fragment RelationshipAttrs on Relationship {
          classifier
          classifierInverse
          annotation
          subjectId
          subjectName
          createdAt
          creatorId
          foreignKey
          id
          name
          pendingRevisions
          relatedId
          relatedName
          status
          type
        }

        fragment TagAttrs on Tag {
          category
          createdAt
          creatorId
          id
          name
          namespace
          pendingRevisions
          slug
          status
          type
          hasExemplaryTagging
          description
        }

        fragment TaggingAttrs on Tagging {
          annotation
          subjectId
          createdAt
          creatorId
          foreignKey
          id
          pendingRevisions
          type
          status
          weight
        }
        """

        # Variables for the query
        variables = {
            "set": card_set,
            "number": collector_number,
            "back": back,
            "moderatorView": moderator_view
        }

        # GraphQL request payload
        payload = {
            "query": query,
            "variables": variables,
            "operationName": "FetchCard"
        }

        print(f"🔍 Fetching tags for {card_set.upper()} #{collector_number}...")

        # Make the GraphQL request
        response = self.session.post(
            f"{self.base_url}/graphql",
            json=payload
        )

        if response.status_code != 200:
            print(f"❌ GraphQL request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None

        try:
            data = response.json()

            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                return None

            print(f"✓ Successfully fetched card data")
            return data

        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON response")
            print(f"Response: {response.text}")
            return None

    def extract_community_tags(self, card_data):
        """Extract and organize community tags from card data"""
        if not card_data or 'data' not in card_data:
            return None

        card = card_data['data']['card']
        if not card:
            return None

        print(f"\n📋 Card: {card['displayName']} ({card['set'].upper()} #{card['collectorNumber']})")
        print(f"🎨 Scryfall URL: {card['scryfallUrl']}")

        # Group tags by namespace
        artwork_tags = []
        card_tags = []
        print_tags = []

        for tagging in card.get('taggings', []):
            tag = tagging['tag']
            tag_info = {
                'name': tag['name'],
                'description': tag['description'],
                'slug': tag['slug'],
                'weight': tagging['weight'],
                'status': tagging['status'],
                'created_at': tagging['createdAt'],
                'namespace': tag['namespace'],
                'category': tag['category'],
                'ancestor_tags': [{'name': t['name'], 'slug': t['slug']} for t in tag.get('ancestorTags', [])]
            }

            if tag['namespace'] == 'artwork':
                artwork_tags.append(tag_info)
            elif tag['namespace'] == 'card':
                card_tags.append(tag_info)
            elif tag['namespace'] == 'print':
                print_tags.append(tag_info)

        print(f"\n🎨 Artwork Tags ({len(artwork_tags)}):")
        for tag in sorted(artwork_tags, key=lambda t: t['name']):
            desc = f" - {tag['description'][:80]}..." if tag['description'] else ""
            print(f"  • {tag['name']}{desc}")

        print(f"\n🃏 Card Tags ({len(card_tags)}):")
        for tag in sorted(card_tags, key=lambda t: t['name']):
            desc = f" - {tag['description'][:80]}..." if tag['description'] else ""
            print(f"  • {tag['name']}{desc}")

        if print_tags:
            print(f"\n🖨️  Print Tags ({len(print_tags)}):")
            for tag in sorted(print_tags, key=lambda t: t['name']):
                desc = f" - {tag['description'][:80]}..." if tag['description'] else ""
                print(f"  • {tag['name']}{desc}")

        # Extract relationships (combo/synergy data)
        relationships = []
        for relationship in card.get('relationships', []):
            rel_info = {
                'name': relationship.get('name', ''),
                'classifier': relationship.get('classifier', ''),
                'classifier_inverse': relationship.get('classifierInverse', ''),
                'annotation': relationship.get('annotation', ''),
                'related_id': relationship.get('relatedId', ''),
                'related_name': relationship.get('relatedName', ''),
                'subject_id': relationship.get('subjectId', ''),
                'subject_name': relationship.get('subjectName', ''),
                'status': relationship.get('status', ''),
                'type': relationship.get('type', ''),
                'created_at': relationship.get('createdAt', ''),
                'creator_id': relationship.get('creatorId', '')
            }
            relationships.append(rel_info)

        if relationships:
            print(f"\n🔗 Relationships ({len(relationships)}):")
            for rel in relationships:
                print(f"  • {rel['name']} → {rel['related_name']} ({rel['classifier']})")

        return {
            'card': {
                'name': card['displayName'],
                'set': card['set'],
                'number': card['collectorNumber'],
                'scryfall_url': card['scryfallUrl'],
                'art_image_url': card['artImageUrl'],
                'card_image_url': card['cardImageUrl'],
                'illustration_id': card['illustrationId'],
                'oracle_id': card['oracleId'],
                'printing_id': card['printingId']
            },
            'artwork_tags': artwork_tags,
            'card_tags': card_tags,
            'print_tags': print_tags,
            'relationships': relationships
        }

def test_api():
    """Test the Scryfall Tagger API with Ajani, Adversary of Tyrants"""

    print("🚀 Testing Scryfall Tagger API")
    print("=" * 50)

    api = ScryfallTaggerAPI()

    try:
        # Test with the card from our network capture
        result = api.fetch_card_tags("m19", "3")

        if result:
            tags = api.extract_community_tags(result)

            if tags:
                print(f"\n📊 Summary:")
                print(f"  Artwork Tags: {len(tags['artwork_tags'])}")
                print(f"  Card Tags: {len(tags['card_tags'])}")
                print(f"  Print Tags: {len(tags['print_tags'])}")

                # Save full data for analysis
                with open('/tmp/scryfall_tag_data.json', 'w') as f:
                    json.dump(tags, f, indent=2)
                print(f"\n💾 Full data saved to: /tmp/scryfall_tag_data.json")

                return True
            else:
                print("❌ Failed to extract tag data")
                return False
        else:
            print("❌ Failed to fetch card data")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_curl_command(card_set="m19", collector_number="3"):
    """Generate a curl command to reproduce the GraphQL request"""

    print("📋 To reproduce this request with curl:")
    print("=" * 50)

    print("1. First, get the CSRF token:")
    print(f'curl -s "https://tagger.scryfall.com/card/{card_set}/{collector_number}" | grep \'csrf-token\' | sed \'s/.*content="\\([^"]*\\)".*/\\1/\'')

    print("\n2. Then make the GraphQL request:")
    print("""curl -X POST 'https://tagger.scryfall.com/graphql' \\
  -H 'Content-Type: application/json' \\
  -H 'X-CSRF-Token: YOUR_CSRF_TOKEN_HERE' \\
  -H 'Referer: https://tagger.scryfall.com/card/m19/3' \\
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36' \\
  --data-raw '{"query":"query FetchCard($set: String!, $number: String!, $back: Boolean = false, $moderatorView: Boolean = false) { card: cardBySet(set: $set, number: $number, back: $back) { artImageUrl backside cardImageUrl collectorNumber displayName id illustrationId layout name oracleId printingId set sideNames flipsideDisplayName hasAlternateName scryfallUrl twoSided rotatedLayout taggings(moderatorView: $moderatorView) { annotation subjectId createdAt creatorId foreignKey id pendingRevisions type status weight tag { category createdAt creatorId id name namespace pendingRevisions slug status type hasExemplaryTagging description ancestorTags { category createdAt creatorId id name namespace pendingRevisions slug status type hasExemplaryTagging description } } } relationships(moderatorView: $moderatorView) { classifier classifierInverse annotation subjectId subjectName createdAt creatorId foreignKey id name pendingRevisions relatedId relatedName status type } } }","variables":{"set":"m19","number":"3","back":false,"moderatorView":false},"operationName":"FetchCard"}' | jq .""")

if __name__ == "__main__":
    success = test_api()
    if success:
        print("\n" + "=" * 50)
        create_curl_command()
    else:
        print("\n❌ API test failed")