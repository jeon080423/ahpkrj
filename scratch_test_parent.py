import streamlit.components.v1 as components
components.html("""
<script>
try {
    const parent = window.parent.document;
    console.log("Parent access:", parent);
} catch(e) {
    console.error("No parent access:", e);
}
</script>
""")
