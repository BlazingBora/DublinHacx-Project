import { SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";
import { colors } from "../theme";

export default function RecipeScreen({ recipe, onBack }) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.backLink} onPress={onBack}>
          ← Scan something else
        </Text>

        <Text style={styles.title}>{recipe.title || "Recipe"}</Text>
        {recipe.servings ? (
          <Text style={styles.muted}>Servings: {recipe.servings}</Text>
        ) : null}

        {recipe.uses_ingredients && recipe.uses_ingredients.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Uses your ingredients</Text>
            {recipe.uses_ingredients.map((ingredient, i) => (
              <Text key={i} style={styles.listItem}>
                • {ingredient}
              </Text>
            ))}
          </View>
        )}

        {recipe.additional_ingredients && recipe.additional_ingredients.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>You'll also need</Text>
            {recipe.additional_ingredients.map((ingredient, i) => (
              <Text key={i} style={styles.listItem}>
                • {ingredient}
              </Text>
            ))}
          </View>
        )}

        {recipe.steps && recipe.steps.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Steps</Text>
            {recipe.steps.map((step, i) => (
              <Text key={i} style={styles.listItem}>
                {i + 1}. {step}
              </Text>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  container: {
    padding: 20,
    paddingBottom: 40,
  },
  backLink: {
    color: colors.accent,
    marginBottom: 20,
    fontSize: 15,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: "800",
    marginBottom: 4,
  },
  muted: {
    color: colors.muted,
    fontSize: 14,
  },
  section: {
    marginTop: 24,
  },
  sectionTitle: {
    color: colors.accent,
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 8,
  },
  listItem: {
    color: colors.text,
    fontSize: 15,
    marginBottom: 6,
    lineHeight: 21,
  },
});
