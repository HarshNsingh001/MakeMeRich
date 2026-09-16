import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { colors } from '../theme/colors';

export default function AgentDebateScreen({ route, navigation }: any) {
  const { symbol, analysis } = route.params;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>{symbol} Agent Debate</Text>
      </View>

      <ScrollView style={styles.content}>
        {(analysis?.agent_evidence || []).map((agent: any, idx: number) => (
          <View key={idx} style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.agentName}>🤖 {agent.agent}</Text>
              <Text style={agent.confidence > 0.7 ? styles.confGreen : styles.confYellow}>
                {(agent.confidence * 100).toFixed(0)}%
              </Text>
            </View>
            <Text style={styles.thesis}>{agent.thesis}</Text>
          </View>
        ))}

        {analysis?.critic_feedback && (
          <View style={[styles.card, { borderColor: colors.accentYellow + '55', backgroundColor: colors.accentYellow + '11' }]}>
            <Text style={styles.criticTitle}>Adversarial Critic</Text>
            <Text style={styles.thesis}>{analysis.critic_feedback}</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  header: { padding: 20, paddingTop: 60, borderBottomWidth: 1, borderColor: colors.border },
  backBtn: { color: colors.textSecondary, marginBottom: 10 },
  title: { fontSize: 24, fontWeight: 'bold', color: colors.textPrimary },
  content: { padding: 20 },
  card: { backgroundColor: colors.bgCard, padding: 16, borderRadius: 12, borderWidth: 1, borderColor: colors.border, marginBottom: 16 },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  agentName: { fontSize: 16, fontWeight: 'bold', color: colors.textPrimary },
  confGreen: { color: colors.accentGreen, fontWeight: 'bold' },
  confYellow: { color: colors.accentYellow, fontWeight: 'bold' },
  thesis: { color: colors.textSecondary, lineHeight: 22 },
  criticTitle: { color: colors.accentYellow, fontWeight: 'bold', marginBottom: 8 }
});
