import { useState } from "react";
import { Alert, FlatList, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { getRecipe } from "../api";
import ItemCard from "../components/ItemCard";
import LoadingButton from "../components/LoadingButton";
import { colors, severityColor } from "../theme";

export default function ResultsScreen({ mode, items, interactions, onBack, onRecipe }) {
  const [selected, setSelected] = useState({});
  const [generating, setGenerating] = useState(false);

  const toggleSelect = (name) => {
    setSelected((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const handleGenerateRecipe = async () => {
    const ingredients = Object.keys(selected).filter((name) => selected[name]);

    if (ingredients.length === 0) {
      Alert.alert("Pick some ingredients", "Select at least one item to build a recipe.");
      return;
    }

    setGenerating(true);
    try {
      const data = await getRecipe(ingredients);
      onRecipe(data.recipe);
    } catch (err) {
      Alert.alert("Recipe failed", err.message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <FlatList
        data={items}
        keyExtractor={(item, index) => `${item.name}-${index}`}
        contentContainerStyle={styles.container}
        ListHeaderComponent={
          <>
            <Text style={styles.backLink} onPress={onBack}>
              ← Scan something else
            </Text>

            {mode === "medication" && (
              <View style={styles.notice}>
                <Text style={styles.noticeText}>
                  ⚠️ Expiration dates are read directly from the label. This is
                  not medical advice - check with your pharmacist before taking
                  any medication you're unsure about.
                </Text>
              </View>
            )}

            {interactions && interactions.length > 0 && (
              <View style={styles.interactions}>
                <Text style={styles.interactionsTitle}>
                  ⚠️ Possible food-medication interactions
                </Text>
                <Text style={styles.muted}>
                  Based on a curated reference list, not medical advice - confirm
                  with your pharmacist or doctor.
                </Text>
                {interactions.map((warning, i) => (
                  <View
                    key={i}
                    style={[
                      styles.interactionCard,
                      { borderLeftColor: severityColor(warning.severity) },
                    ]}
                  >
                    <Text style={styles.interactionHeadline}>
                      {warning.food} + {warning.drug}
                    </Text>
                    <Text style={styles.muted}>{warning.risk}</Text>
                  </View>
                ))}
              </View>
            )}

            {items.length === 0 && <Text style={styles.muted}>No items found.</Text>}
          </>
        }
        renderItem={({ item }) => (
          <ItemCard
            item={item}
            mode={mode}
            selectable={mode === "grocery"}
            selected={!!selected[item.name]}
            onToggleSelect={() => toggleSelect(item.name)}
          />
        )}
        ListFooterComponent={
          mode === "grocery" && items.length > 0 ? (
            <LoadingButton
              label="🍳 Generate Recipe from Selected"
              loadingLabel="Cooking up a recipe..."
              loading={generating}
              onPress={handleGenerateRecipe}
              style={styles.recipeButton}
            />
          ) : null
        }
      />
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
  },
  backLink: {
    color: colors.accent,
    marginBottom: 20,
    fontSize: 15,
  },
  notice: {
    backgroundColor: "#332a12",
    borderWidth: 1,
    borderColor: "#5c4a1f",
    borderRadius: 8,
    padding: 12,
    marginBottom: 20,
  },
  noticeText: {
    color: colors.soon,
    fontSize: 13,
    lineHeight: 18,
  },
  interactions: {
    marginBottom: 20,
  },
  interactionsTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 4,
  },
  interactionCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderLeftWidth: 4,
    borderRadius: 8,
    padding: 12,
    marginTop: 10,
  },
  interactionHeadline: {
    color: colors.text,
    fontWeight: "700",
    marginBottom: 4,
  },
  muted: {
    color: colors.muted,
    fontSize: 13,
  },
  recipeButton: {
    marginTop: 12,
    marginBottom: 32,
  },
});
