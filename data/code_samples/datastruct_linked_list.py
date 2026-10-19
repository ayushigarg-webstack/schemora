class ListNode:
    """Represents a single node in a singly linked list."""
    def __init__(self, value):
        self.value = value
        self.next = None

class LinkedList:
    """Simple singly linked list with append and traverse operations."""
    def __init__(self):
        self.head = None

    def append(self, value):
        new_node = ListNode(value)
        if not self.head:
            self.head = new_node
            return
        current = self.head
        while current.next:
            current = current.next
        current.next = new_node

    def to_list(self):
        elements = []
        current = self.head
        while current:
            elements.append(current.value)
            current = current.next
        return elements

# Example execution
ll = LinkedList()
ll.append(10)
ll.append(20)
items = ll.to_list()
